#!/usr/bin/env bash
set -e

echo "=== [SQLArena Docker Init] Creating databases & read-only sandbox role ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    CREATE DATABASE enterprise_db;
    CREATE DATABASE sqlarena_db;
    DO \$\$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sqlarena_ai_ro') THEN
        CREATE ROLE sqlarena_ai_ro WITH LOGIN PASSWORD 'sqlarena_ro' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;
      END IF;
    END
    \$\$;
EOSQL

echo "=== [SQLArena Docker Init] Loading Enterprise Dataset (13 tables, >13,400 rows) ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "enterprise_db" -f /sqlarena-postgre/enterprise_db/schema_code.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "enterprise_db" -f /sqlarena-postgre/enterprise_db/constraint.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "enterprise_db" -f /sqlarena-postgre/enterprise_db/enterprise_seed_data.sql

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "enterprise_db" <<-EOSQL
    REVOKE ALL ON DATABASE enterprise_db FROM PUBLIC;
    GRANT CONNECT ON DATABASE enterprise_db TO sqlarena_ai_ro;
    GRANT USAGE ON SCHEMA public TO sqlarena_ai_ro;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO sqlarena_ai_ro;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO sqlarena_ai_ro;
    ALTER ROLE sqlarena_ai_ro SET default_transaction_read_only = on;
    ALTER ROLE sqlarena_ai_ro SET statement_timeout = '10s';
EOSQL

echo "=== [SQLArena Docker Init] Loading Legacy Compatibility Tables in sqlarena_db ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "sqlarena_db" -f /sqlarena-postgre/sqlarena_db/01_create_sqlarena_db.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "sqlarena_db" -f /sqlarena-postgre/sqlarena_db/02_seed_sqlarena_db.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "sqlarena_db" -f /sqlarena-postgre/app_db/01_create_app_tables.sql

echo "=== [SQLArena Docker Init] Completed Successfully! ==="
