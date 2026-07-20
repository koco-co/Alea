-- Applied through the Supabase plugin before the schema push.
-- Password rotation is intentionally out of band and must use hidden operator input.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'alea_api') then
    create role alea_api login nosuperuser nocreatedb nocreaterole noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'alea_worker') then
    create role alea_worker login nosuperuser nocreatedb nocreaterole noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'alea_dispatcher') then
    create role alea_dispatcher login nosuperuser nocreatedb nocreaterole noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'alea_scheduler') then
    create role alea_scheduler login nosuperuser nocreatedb nocreaterole noinherit;
  end if;
end
$$;

-- The migration operator may assume each isolated runtime role for permission
-- verification, but never inherits its privileges implicitly.
grant alea_api to postgres with inherit false, set true;
grant alea_worker to postgres with inherit false, set true;
grant alea_dispatcher to postgres with inherit false, set true;
grant alea_scheduler to postgres with inherit false, set true;
