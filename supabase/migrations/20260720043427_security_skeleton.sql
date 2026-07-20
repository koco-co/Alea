-- Alea security skeleton: Auth profile lifecycle and consent enforcement.

create or replace function handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public, auth, pg_temp
as $$
begin
  insert into public.profiles (id, status, display_name)
  values (
    new.id,
    'pending_consent',
    nullif(trim(coalesce(new.raw_user_meta_data ->> 'display_name', '')), '')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function handle_new_auth_user();

create or replace function protect_profile_privileges()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if (new.role, new.status) is distinct from (old.role, old.status)
     and not is_admin()
     and not (
       old.id = auth.uid()
       and old.role = 'user'
       and new.role = 'user'
       and old.status = 'pending_consent'
       and new.status = 'active'
       and current_setting('app.consent_activation', true) = 'allowed'
     ) then
    raise exception 'profile role and status require an administrator' using errcode = '42501';
  end if;
  new.updated_at := now();
  return new;
end;
$$;

create function record_current_user_consent(
  p_age_confirmed boolean,
  p_terms_accepted boolean,
  p_terms_version text,
  p_privacy_version text,
  p_risk_version text
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_user_id uuid := auth.uid();
begin
  if v_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if not coalesce(p_age_confirmed, false) or not coalesce(p_terms_accepted, false) then
    raise exception 'age and terms confirmations are required' using errcode = '23514';
  end if;
  if trim(coalesce(p_terms_version, '')) = ''
     or trim(coalesce(p_privacy_version, '')) = ''
     or trim(coalesce(p_risk_version, '')) = '' then
    raise exception 'consent versions are required' using errcode = '23514';
  end if;

  insert into user_consents (
    user_id, age_confirmed, terms_version, privacy_version, risk_version
  ) values (
    v_user_id, true, p_terms_version, p_privacy_version, p_risk_version
  ) on conflict (user_id, terms_version, privacy_version, risk_version)
    do update set age_confirmed = true, consented_at = now(), revoked_at = null;

  perform set_config('app.consent_activation', 'allowed', true);
  update profiles
    set status = 'active'
    where id = v_user_id and role = 'user' and status = 'pending_consent';
end;
$$;

create function reject_current_user_consent()
returns void
language plpgsql
security definer
set search_path = public, auth, pg_temp
as $$
declare
  v_user_id uuid := auth.uid();
begin
  if v_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if exists (
    select 1 from public.profiles
    where id = v_user_id and status <> 'pending_consent'
  ) then
    raise exception 'only pending consent accounts can be rejected' using errcode = '42501';
  end if;
  delete from auth.users where id = v_user_id;
end;
$$;

create function record_user_consent_from_signup(
  p_user_id uuid,
  p_terms_version text,
  p_privacy_version text,
  p_risk_version text
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if coalesce(current_setting('request.jwt.claim.role', true), current_user) <> 'service_role' then
    raise exception 'service role required' using errcode = '42501';
  end if;
  if not exists (select 1 from profiles where id = p_user_id and status = 'pending_consent') then
    raise exception 'pending profile not found' using errcode = 'P0002';
  end if;
  insert into user_consents (
    user_id, age_confirmed, terms_version, privacy_version, risk_version
  ) values (
    p_user_id, true, p_terms_version, p_privacy_version, p_risk_version
  ) on conflict (user_id, terms_version, privacy_version, risk_version)
    do update set age_confirmed = true, consented_at = now(), revoked_at = null;
  perform set_config('app.consent_activation', 'allowed', true);
  update profiles set status = 'active' where id = p_user_id;
end;
$$;

revoke all on function handle_new_auth_user() from public;
revoke all on function record_current_user_consent(boolean, boolean, text, text, text) from public;
revoke all on function reject_current_user_consent() from public;
revoke all on function record_user_consent_from_signup(uuid, text, text, text) from public;
grant execute on function record_current_user_consent(boolean, boolean, text, text, text) to authenticated;
grant execute on function reject_current_user_consent() to authenticated;
grant execute on function record_user_consent_from_signup(uuid, text, text, text) to service_role;
