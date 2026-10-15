-- =====================================================
-- 03_create_readonly_role.sql   (chay bang tai khoan postgres, ket noi enterprise_db)
-- Tao role chi doc cho pipeline kiem duyet. ai/review.py tu choi chay neu role con
-- quyen ghi / CREATE / TEMP (ham verify_readonly trong ai/validator.py).
--
-- TRUOC KHI CHAY: doi 'DOI_MAT_KHAU_NAY' thanh mat khau rieng cua ban.
-- Sau do dien ENTERPRISE_DB_USER=sqlarena_ai_ro va ENTERPRISE_DB_PASSWORD trong ai/.env
-- =====================================================

DO $$
BEGIN
    IF current_database() <> 'enterprise_db' THEN
        RAISE EXCEPTION 'Wrong database. Connect to enterprise_db.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sqlarena_ai_ro') THEN
        CREATE ROLE sqlarena_ai_ro LOGIN PASSWORD 'DOI_MAT_KHAU_NAY'
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
    END IF;
END $$;

-- PostgreSQL mac dinh cho PUBLIC quyen TEMP tren moi database -> phai go.
REVOKE CREATE, TEMPORARY ON DATABASE enterprise_db FROM PUBLIC;
GRANT CONNECT ON DATABASE enterprise_db TO sqlarena_ai_ro;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO sqlarena_ai_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sqlarena_ai_ro;

ALTER ROLE sqlarena_ai_ro SET default_transaction_read_only = on;
ALTER ROLE sqlarena_ai_ro SET statement_timeout = '15s';

-- Kiem tra: 3 dong phai tra ve false / false / true
SELECT has_database_privilege('sqlarena_ai_ro', 'enterprise_db', 'TEMP')      AS temp_priv,
       has_schema_privilege('sqlarena_ai_ro', 'public', 'CREATE')              AS create_priv,
       has_table_privilege('sqlarena_ai_ro', 'public.orders', 'SELECT')        AS can_select;
