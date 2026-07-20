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
