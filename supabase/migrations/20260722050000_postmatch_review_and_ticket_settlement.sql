-- Close the two post-settlement gaps: post-match review is a real frozen
-- Provider phase, and bet positions are settled through append-only account
-- entries instead of being silently left at a pending balance.

alter table public.settlement_positions
  add column if not exists plan jsonb;

create table public.settlement_position_plans (
  id uuid primary key default gen_random_uuid(),
  position_id uuid not null unique references public.settlement_positions(id),
  settlement_run_id uuid not null references public.settlement_runs(id),
  plan jsonb not null,
  payload_hash text not null,
  created_at timestamptz not null default now()
);

create table public.postmatch_review_contexts (
  id uuid primary key default gen_random_uuid(),
  settlement_run_id uuid not null unique references public.settlement_runs(id),
  notarized_prediction_id uuid not null references public.notarized_predictions(id),
  result_version_id uuid not null references public.match_results(id),
  payload jsonb not null,
  payload_hash text not null,
  frozen_at timestamptz not null default now(),
  unique (notarized_prediction_id, result_version_id)
);

create table public.settlement_reviews (
  id uuid primary key default gen_random_uuid(),
  settlement_run_id uuid not null unique references public.settlement_runs(id),
  context_id uuid not null unique references public.postmatch_review_contexts(id),
  state text not null check (state in ('scheduled', 'running', 'completed', 'failed')),
  phase_count integer not null default 0 check (phase_count >= 0),
  completed_at timestamptz,
  error_code text,
  created_at timestamptz not null default now(),
  check ((state = 'completed' and completed_at is not null) or state <> 'completed')
);

create table public.settlement_position_settlements (
  id uuid primary key default gen_random_uuid(),
  position_id uuid not null unique references public.settlement_positions(id),
  settlement_run_id uuid not null references public.settlement_runs(id),
  result_version_id uuid not null references public.match_results(id),
  state text not null check (state in ('settled_hit', 'settled_miss', 'settled_refund')),
  stake numeric(14,2) not null check (stake >= 0),
  returned_amount numeric(14,2) not null check (returned_amount >= 0),
  created_at timestamptz not null default now(),
  check (state <> 'settled_miss' or returned_amount = 0),
  unique (position_id, result_version_id)
);
create index settlement_position_settlements_run_idx
  on public.settlement_position_settlements(settlement_run_id);

create or replace function public.apply_settlement_position(
  p_position_id uuid,
  p_state text,
  p_returned_amount numeric
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_position public.settlement_positions%rowtype;
  v_run public.settlement_runs%rowtype;
  v_result public.match_results%rowtype;
  v_existing public.settlement_position_settlements%rowtype;
  v_balance numeric(14,2);
  v_after numeric(14,2);
  v_stake_entry uuid;
  v_return_entry uuid;
begin
  if session_user <> 'alea_worker'
     and coalesce(current_setting('role', true), 'none') <> 'alea_worker' then
    raise exception 'apply_settlement_position requires alea_worker' using errcode = '42501';
  end if;
  if p_state not in ('settled_hit', 'settled_miss', 'settled_refund') then
    raise exception 'invalid settlement position state' using errcode = '22023';
  end if;
  if p_returned_amount is null or p_returned_amount < 0 then
    raise exception 'returned amount must be non-negative' using errcode = '22023';
  end if;

  select * into v_position
  from public.settlement_positions
  where id = p_position_id
  for update;
  if not found then
    raise exception 'settlement position not found' using errcode = 'P0002';
  end if;
  select * into v_run from public.settlement_runs where id = v_position.settlement_run_id;
  select * into v_result from public.match_results where id = v_run.result_version_id;

  select * into v_existing
  from public.settlement_position_settlements
  where position_id = p_position_id
    and result_version_id = v_run.result_version_id;
  if found then
    return jsonb_build_object(
      'status', 'idempotent_replay',
      'position_id', p_position_id,
      'settlement_position_settlement_id', v_existing.id,
      'account_id', v_position.account_id
    );
  end if;

  if v_position.decision = 'no_bet' then
    if p_returned_amount <> 0 or p_state <> 'settled_refund' then
      raise exception 'no_bet position cannot create a payout' using errcode = '23514';
    end if;
  end if;
  if v_position.decision = 'bet' and p_state = 'settled_miss' and p_returned_amount <> 0 then
    raise exception 'a miss cannot return money' using errcode = '23514';
  end if;

  insert into public.settlement_position_settlements(
    position_id, settlement_run_id, result_version_id, state, stake, returned_amount
  ) values (
    v_position.id, v_position.settlement_run_id, v_run.result_version_id,
    p_state, v_position.stake, p_returned_amount
  );

  select current_balance into v_balance
  from public.simulated_accounts
  where id = v_position.account_id
  for update;
  if not found then
    raise exception 'settlement account not found' using errcode = 'P0002';
  end if;

  if v_position.stake > 0 then
    if v_balance < v_position.stake then
      raise exception 'settlement account has insufficient balance' using errcode = '23514';
    end if;
    v_after := v_balance - v_position.stake;
    insert into public.simulated_account_entries(
      account_id, settlement_run_id, result_version_id, entry_type, amount, balance_after
    ) values (
      v_position.account_id, v_position.settlement_run_id, v_run.result_version_id,
      'stake', -v_position.stake, v_after
    ) returning id into v_stake_entry;
    update public.simulated_accounts
    set current_balance = v_after, updated_at = now()
    where id = v_position.account_id;
    v_balance := v_after;
  end if;

  if p_returned_amount > 0 then
    v_after := v_balance + p_returned_amount;
    insert into public.simulated_account_entries(
      account_id, settlement_run_id, result_version_id, entry_type, amount, balance_after
    ) values (
      v_position.account_id, v_position.settlement_run_id, v_run.result_version_id,
      case when p_state = 'settled_refund' then 'refund' else 'payout' end,
      p_returned_amount, v_after
    ) returning id into v_return_entry;
    update public.simulated_accounts
    set current_balance = v_after, updated_at = now()
    where id = v_position.account_id;
  end if;

  return jsonb_build_object(
    'status', 'settled',
    'position_id', p_position_id,
    'state', p_state,
    'stake_entry_id', v_stake_entry,
    'return_entry_id', v_return_entry,
    'account_id', v_position.account_id,
    'balance_after', coalesce(v_after, v_balance)
  );
end;
$$;

alter table public.postmatch_review_contexts enable row level security;
alter table public.settlement_reviews enable row level security;
alter table public.settlement_position_settlements enable row level security;
alter table public.settlement_position_plans enable row level security;

create policy worker_postmatch_review_contexts_all on public.postmatch_review_contexts
  for all to alea_worker using (true) with check (true);
create policy worker_settlement_reviews_all on public.settlement_reviews
  for all to alea_worker using (true) with check (true);
create policy worker_position_settlements_all on public.settlement_position_settlements
  for all to alea_worker using (true) with check (true);
create policy worker_position_plans_all on public.settlement_position_plans
  for all to alea_worker using (true) with check (true);
create policy worker_settlement_odds_read on public.match_odds_snapshots
  for select to alea_worker using (true);

revoke all on public.postmatch_review_contexts, public.settlement_reviews,
  public.settlement_position_settlements, public.settlement_position_plans
  from public, anon, authenticated;
grant select, insert on public.postmatch_review_contexts to alea_worker;
grant select, insert, update on public.settlement_reviews to alea_worker;
grant select, insert on public.settlement_position_settlements to alea_worker;
grant select, insert on public.settlement_position_plans to alea_worker;
grant select on public.match_odds_snapshots to alea_worker;
grant execute on function public.apply_settlement_position(uuid, text, numeric) to alea_worker;
revoke all on function public.apply_settlement_position(uuid, text, numeric)
  from public, anon, authenticated;

create trigger postmatch_review_contexts_immutable
before update or delete on public.postmatch_review_contexts
for each row execute function reject_immutable_mutation();
create trigger settlement_position_settlements_immutable
before update or delete on public.settlement_position_settlements
for each row execute function reject_immutable_mutation();
create trigger settlement_position_plans_immutable
before update or delete on public.settlement_position_plans
for each row execute function reject_immutable_mutation();
