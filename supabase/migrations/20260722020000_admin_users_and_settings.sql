-- Complete the admin users/settings gateway used by the production console.
-- These functions are SECURITY DEFINER so the API role never receives direct
-- access to auth.users; every mutation is authorized and audited in one txn.

create or replace function public.protect_profile_privileges()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if (new.role, new.status) is distinct from (old.role, old.status)
     and not is_admin()
     and coalesce(current_setting('alea.admin_mutation', true), 'off') <> 'on' then
    raise exception 'profile role and status require an administrator' using errcode = '42501';
  end if;
  new.updated_at := now();
  return new;
end;
$$;

create or replace function public.alea_query_list_users(
  p_actor_id text,
  p_params jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor uuid := nullif(p_actor_id, '')::uuid;
  v_search text := nullif(trim(coalesce(p_params->>'search', '')), '');
  v_status profile_status := nullif(p_params->>'status', '')::profile_status;
  v_limit integer := least(greatest(coalesce((p_params->>'limit')::integer, 50), 1), 200);
  v_items jsonb;
begin
  if not exists (
    select 1 from profiles where id = v_actor and role = 'admin' and status = 'active'
  ) then
    raise exception 'administrator_required' using errcode = '42501';
  end if;

  select coalesce(jsonb_agg(to_jsonb(row_data) order by row_data.created_at desc), '[]'::jsonb)
    into v_items
  from (
    select
      p.id,
      coalesce(nullif(p.display_name, ''), '未命名用户') as name,
      u.email,
      p.role::text,
      p.status::text,
      p.created_at as joined,
      p.created_at
    from profiles p
    join auth.users u on u.id = p.id
    where (v_search is null or coalesce(p.display_name, '') ilike '%' || v_search || '%'
           or coalesce(u.email, '') ilike '%' || v_search || '%')
      and (v_status is null or p.status = v_status)
    order by p.created_at desc
    limit v_limit
  ) row_data;

  return jsonb_build_object('items', v_items, 'next_cursor', null);
end;
$$;

create or replace function public.alea_command_disable_user(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor uuid := nullif(p_actor_id, '')::uuid;
  v_user uuid := nullif(p_payload->>'user_id', '')::uuid;
  v_reason text := trim(coalesce(p_payload->>'reason', ''));
  v_profile profiles%rowtype;
begin
  if not exists (
    select 1 from profiles where id = v_actor and role = 'admin' and status = 'active'
  ) then
    raise exception 'administrator_required' using errcode = '42501';
  end if;
  if coalesce((p_payload->>'confirmed')::boolean, false) is not true or char_length(v_reason) = 0 then
    raise exception 'user_status_confirmation_required' using errcode = '22023';
  end if;

  select * into v_profile from profiles where id = v_user for update;
  if not found then raise exception 'user_not_found' using errcode = 'P0002'; end if;
  if v_profile.role = 'admin' then raise exception 'admin_user_status_forbidden' using errcode = '42501'; end if;

  perform set_config('alea.admin_mutation', 'on', true);
  update profiles set status = 'disabled' where id = v_user returning * into v_profile;
  insert into admin_audit_logs(actor_id, action, target_type, target_id, request_id, detail_redacted)
    values (v_actor, 'disable_user', 'profile', v_user::text, p_request_id,
            jsonb_build_object('reason', left(v_reason, 1000)));
  return jsonb_build_object('id', v_profile.id, 'status', v_profile.status::text);
end;
$$;

create or replace function public.alea_command_restore_user(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor uuid := nullif(p_actor_id, '')::uuid;
  v_user uuid := nullif(p_payload->>'user_id', '')::uuid;
  v_reason text := trim(coalesce(p_payload->>'reason', ''));
  v_profile profiles%rowtype;
begin
  if not exists (
    select 1 from profiles where id = v_actor and role = 'admin' and status = 'active'
  ) then
    raise exception 'administrator_required' using errcode = '42501';
  end if;
  if coalesce((p_payload->>'confirmed')::boolean, false) is not true or char_length(v_reason) = 0 then
    raise exception 'user_status_confirmation_required' using errcode = '22023';
  end if;

  select * into v_profile from profiles where id = v_user for update;
  if not found then raise exception 'user_not_found' using errcode = 'P0002'; end if;
  if v_profile.role = 'admin' then raise exception 'admin_user_status_forbidden' using errcode = '42501'; end if;

  perform set_config('alea.admin_mutation', 'on', true);
  update profiles set status = 'active' where id = v_user returning * into v_profile;
  insert into admin_audit_logs(actor_id, action, target_type, target_id, request_id, detail_redacted)
    values (v_actor, 'restore_user', 'profile', v_user::text, p_request_id,
            jsonb_build_object('reason', left(v_reason, 1000)));
  return jsonb_build_object('id', v_profile.id, 'status', v_profile.status::text);
end;
$$;

create or replace function public.alea_query_read_settings(
  p_actor_id text,
  p_params jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor uuid := nullif(p_actor_id, '')::uuid;
  v_group text := p_params->>'group';
  v_items jsonb;
begin
  if not exists (
    select 1 from profiles where id = v_actor and role = 'admin' and status = 'active'
  ) then
    raise exception 'administrator_required' using errcode = '42501';
  end if;

  select coalesce(jsonb_agg(jsonb_build_object(
    'setting_key', s.key,
    'version', s.version,
    'value', s.value,
    'change_note', 'seeded or published version',
    'created_by', coalesce(s.released_by::text, 'system'),
    'created_at', s.created_at,
    'read_only', true
  ) order by s.key, s.version desc), '[]'::jsonb)
    into v_items
  from system_setting_versions s
  where s.key = v_group
     or (v_group = 'scoring_rules' and s.key in ('score_formula', 'sporttery_rules'))
     or (v_group = 'ledger_risk' and s.key = 'risk_limits')
     or (v_group = 'data_automation' and s.key in ('methodology_trigger', 'history_context_limits'))
     or (v_group = 'user_management' and false)
     or (v_group = 'prompts_methodology' and s.key in ('methodology_trigger'));

  return jsonb_build_object('group', v_group, 'items', v_items);
end;
$$;

create or replace function public.alea_command_save_settings_version(
  p_actor_id text,
  p_request_id text,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_actor uuid := nullif(p_actor_id, '')::uuid;
  v_group text := nullif(trim(p_payload->>'group'), '');
  v_value jsonb := coalesce(p_payload->'value', '{}'::jsonb);
  v_note text := trim(coalesce(p_payload->>'change_note', ''));
  v_key text;
  v_version integer;
  v_expected integer := nullif(p_payload->>'expected_version', '')::integer;
  v_row system_setting_versions%rowtype;
begin
  if not exists (
    select 1 from profiles where id = v_actor and role = 'admin' and status = 'active'
  ) then
    raise exception 'administrator_required' using errcode = '42501';
  end if;
  if v_group is null or char_length(v_note) = 0 or jsonb_typeof(v_value) <> 'object' then
    raise exception 'invalid_settings_payload' using errcode = '22023';
  end if;
  if v_group not in ('scoring_rules', 'ledger_risk', 'data_automation', 'user_management', 'prompts_methodology') then
    raise exception 'invalid_settings_group' using errcode = '22023';
  end if;

  v_key := v_group;
  select coalesce(max(version), 0) + 1 into v_version from system_setting_versions where key = v_key;
  if v_expected is not null and v_expected <> v_version - 1 then
    raise exception 'settings_version_conflict' using errcode = '40001';
  end if;
  insert into system_setting_versions(key, version, value, released_by, effective_at)
    values (v_key, v_version, v_value, v_actor, now())
    returning * into v_row;
  insert into admin_audit_logs(actor_id, action, target_type, target_id, request_id, detail_redacted)
    values (v_actor, 'save_settings_version', 'system_setting', v_key, p_request_id,
            jsonb_build_object('version', v_version, 'change_note', left(v_note, 1000)));
  return jsonb_build_object(
    'group', v_group,
    'version', v_row.version,
    'value', v_row.value,
    'change_note', v_note,
    'created_by', v_actor::text,
    'created_at', v_row.created_at,
    'read_only', true
  );
end;
$$;

revoke all on function public.alea_query_list_users(text, jsonb) from public;
revoke all on function public.alea_command_disable_user(text, text, jsonb) from public;
revoke all on function public.alea_command_restore_user(text, text, jsonb) from public;
revoke all on function public.alea_query_read_settings(text, jsonb) from public;
revoke all on function public.alea_command_save_settings_version(text, text, jsonb) from public;
grant execute on function public.alea_query_list_users(text, jsonb) to alea_api;
grant execute on function public.alea_command_disable_user(text, text, jsonb) to alea_api;
grant execute on function public.alea_command_restore_user(text, text, jsonb) to alea_api;
grant execute on function public.alea_query_read_settings(text, jsonb) to alea_api;
grant execute on function public.alea_command_save_settings_version(text, text, jsonb) to alea_api;
