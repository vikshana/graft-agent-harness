-- The synthetic application probe must exercise PostgreSQL RLS as a
-- non-superuser. The bootstrap role owns the disposable database; the role
-- used through transaction-mode PgBouncer owns only the synthetic tables.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gate03') THEN
        CREATE ROLE gate03 LOGIN PASSWORD 'gate03_local_only' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE gate03_app TO gate03;
GRANT USAGE, CREATE ON SCHEMA public TO gate03;
