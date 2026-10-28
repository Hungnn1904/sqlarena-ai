-- Core v2 data. Standalone UTF-8 SQL; Reference SQL is stored as TEXT only.
BEGIN;

SET LOCAL search_path=pg_catalog,public;
SET LOCAL standard_conforming_strings=on;
SET LOCAL lock_timeout='5s';

DO $database_guard$
BEGIN
    IF current_database() <> 'sqlarena_db' THEN
        RAISE EXCEPTION 'Wrong database: connect Query Tool to sqlarena_db before running this file.';
    END IF;
END
$database_guard$;

DO $shape_guard_v2$
DECLARE
    expected jsonb := $core_expected_shape_v2${
  "tables": [
    {
      "name": "worlds",
      "columns": [
        {
          "name": "world_id",
          "type": "character varying(100)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "name",
          "type": "character varying(150)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "database_name",
          "type": "character varying(100)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "dialect",
          "type": "character varying(30)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "schema_description",
          "type": "jsonb",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "fk_relations",
          "type": "jsonb",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "business_rules",
          "type": "jsonb",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "planted_traps",
          "type": "jsonb",
          "nullable": false,
          "default": "'[]'::jsonb",
          "identity": "",
          "generated": ""
        },
        {
          "name": "allowed_sql_features",
          "type": "jsonb",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        }
      ],
      "constraints": {
        "core_worlds_pk": "PRIMARY KEY (world_id)"
      }
    },
    {
      "name": "skills",
      "columns": [
        {
          "name": "skill_id",
          "type": "character varying(30)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "name",
          "type": "character varying(160)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "category",
          "type": "character varying(100)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "base_difficulty",
          "type": "character varying(10)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        }
      ],
      "constraints": {
        "core_skills_pk": "PRIMARY KEY (skill_id)",
        "core_skills_base_difficulty_check": "CHECK (base_difficulty::text = ANY (ARRAY['easy','medium','hard']::text[]))"
      }
    },
    {
      "name": "templates",
      "columns": [
        {
          "name": "template_id",
          "type": "bigint",
          "nullable": false,
          "default": null,
          "identity": "d",
          "generated": ""
        },
        {
          "name": "world_id",
          "type": "character varying(100)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "topic",
          "type": "character varying(150)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "difficulty",
          "type": "character varying(10)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "pattern",
          "type": "text",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "constraints",
          "type": "jsonb",
          "nullable": false,
          "default": "'{}'::jsonb",
          "identity": "",
          "generated": ""
        }
      ],
      "constraints": {
        "core_templates_pk": "PRIMARY KEY (template_id)",
        "core_templates_world_fk": "FOREIGN KEY (world_id) REFERENCES core.worlds(world_id)",
        "core_templates_difficulty_check": "CHECK (difficulty::text = ANY (ARRAY['easy','medium','hard']::text[]))"
      }
    },
    {
      "name": "source_questions",
      "columns": [
        {
          "name": "question_id",
          "type": "character varying(30)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "world_id",
          "type": "character varying(100)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "title",
          "type": "text",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "question_text",
          "type": "text",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "reference_sql",
          "type": "text",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "expected_result",
          "type": "jsonb",
          "nullable": true,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "difficulty",
          "type": "character varying(10)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "primary_skill_group",
          "type": "character varying(30)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "primary_business_domain",
          "type": "character varying(100)",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "skills",
          "type": "jsonb",
          "nullable": false,
          "default": "'[]'::jsonb",
          "identity": "",
          "generated": ""
        },
        {
          "name": "depth",
          "type": "integer",
          "nullable": true,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "metadata",
          "type": "jsonb",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "validation",
          "type": "jsonb",
          "nullable": false,
          "default": null,
          "identity": "",
          "generated": ""
        },
        {
          "name": "created_at",
          "type": "timestamp with time zone",
          "nullable": false,
          "default": "now()",
          "identity": "",
          "generated": ""
        }
      ],
      "constraints": {
        "core_source_questions_pk": "PRIMARY KEY (question_id)",
        "core_source_questions_world_fk": "FOREIGN KEY (world_id) REFERENCES core.worlds(world_id)",
        "core_source_questions_skill_fk": "FOREIGN KEY (primary_skill_group) REFERENCES core.skills(skill_id)",
        "core_source_questions_difficulty_check": "CHECK (difficulty::text = ANY (ARRAY['easy','medium','hard']::text[]))",
        "core_source_questions_depth_check": "CHECK (depth IS NULL OR depth >= 0)"
      }
    }
  ],
  "indexes": {
    "idx_core_templates_world": "CREATE INDEX idx_core_templates_world ON core.templates USING btree (world_id)",
    "idx_core_source_questions_world": "CREATE INDEX idx_core_source_questions_world ON core.source_questions USING btree (world_id)",
    "idx_core_source_questions_difficulty": "CREATE INDEX idx_core_source_questions_difficulty ON core.source_questions USING btree (difficulty)",
    "idx_core_source_questions_skill": "CREATE INDEX idx_core_source_questions_skill ON core.source_questions USING btree (primary_skill_group)",
    "idx_core_source_questions_domain": "CREATE INDEX idx_core_source_questions_domain ON core.source_questions USING btree (primary_business_domain)"
  }
}$core_expected_shape_v2$::jsonb;
    spec jsonb;
    item record;
    relation_oid oid;
    actual_columns jsonb;
    actual_definition text;
    actual_normalized text;
    expected_normalized text;
    actual_names text[];
BEGIN
    SELECT array_agg(c.relname::text ORDER BY c.relname) INTO actual_names
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='core' AND c.relkind IN ('r','p','v','m','f');
    IF actual_names IS DISTINCT FROM ARRAY['skills','source_questions','templates','worlds']::text[] THEN
        RAISE EXCEPTION 'Core v2 schema mismatch: expected exactly four ordinary tables, found %.', actual_names;
    END IF;
    FOR spec IN SELECT value FROM jsonb_array_elements(expected->'tables') LOOP
        relation_oid := to_regclass(format('core.%I',spec->>'name'));
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE oid=relation_oid AND relkind='r'
                       AND relpersistence='p' AND NOT relrowsecurity AND NOT relforcerowsecurity)
           OR EXISTS (SELECT 1 FROM pg_inherits WHERE inhrelid=relation_oid)
           OR EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid=relation_oid AND NOT tgisinternal) THEN
            RAISE EXCEPTION 'Core v2 schema mismatch in table %: unexpected table properties or triggers.',spec->>'name';
        END IF;
        SELECT jsonb_agg(jsonb_build_object(
            'name',a.attname,'type',format_type(a.atttypid,a.atttypmod),
            'nullable',NOT a.attnotnull,'default',pg_get_expr(d.adbin,d.adrelid),
            'identity',a.attidentity::text,'generated',a.attgenerated::text) ORDER BY a.attnum)
        INTO actual_columns
        FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
        WHERE a.attrelid=relation_oid AND a.attnum>0 AND NOT a.attisdropped;
        IF actual_columns IS DISTINCT FROM spec->'columns' THEN
            RAISE EXCEPTION 'Core v2 column mismatch in table %. Existing tables are not modified.',spec->>'name'
                USING DETAIL=format('Expected: %s. Actual: %s.',spec->'columns',actual_columns);
        END IF;
        IF (SELECT count(*) FROM pg_constraint WHERE conrelid=relation_oid AND contype<>'n')
           <> (SELECT count(*) FROM jsonb_object_keys(spec->'constraints')) THEN
            RAISE EXCEPTION 'Core v2 constraint count mismatch in table %.',spec->>'name';
        END IF;
        FOR item IN SELECT key,value FROM jsonb_each_text(spec->'constraints') LOOP
            SELECT pg_get_constraintdef(oid) INTO actual_definition FROM pg_constraint
            WHERE conrelid=relation_oid AND conname=item.key AND convalidated
                  AND NOT condeferrable AND NOT condeferred;
            actual_normalized := regexp_replace(regexp_replace(actual_definition,
                '::(text|character varying)(\([0-9]+\))?(\[\])?','','g'),'[[:space:]()]','','g');
            expected_normalized := regexp_replace(regexp_replace(item.value,
                '::(text|character varying)(\([0-9]+\))?(\[\])?','','g'),'[[:space:]()]','','g');
            IF actual_normalized IS DISTINCT FROM expected_normalized THEN
                RAISE EXCEPTION 'Core v2 constraint mismatch: %.%',spec->>'name',item.key;
            END IF;
        END LOOP;
    END LOOP;
    IF (SELECT count(*) FROM pg_indexes WHERE schemaname='core') <> 9 THEN
        RAISE EXCEPTION 'Core v2 index count mismatch: expected four PK indexes and five lookup indexes.';
    END IF;
    FOR item IN SELECT key,value FROM jsonb_each_text(expected->'indexes') LOOP
        SELECT pg_get_indexdef(c.oid) INTO actual_definition
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_index i ON i.indexrelid=c.oid
        WHERE n.nspname='core' AND c.relname=item.key AND i.indisvalid AND i.indisready;
        IF regexp_replace(actual_definition,'[[:space:]]','','g')
           IS DISTINCT FROM regexp_replace(item.value,'[[:space:]]','','g') THEN
            RAISE EXCEPTION 'Core v2 index mismatch: %.',item.key;
        END IF;
    END LOOP;
END
$shape_guard_v2$;

LOCK TABLE core.worlds,core.skills,core.templates,core.source_questions IN SHARE ROW EXCLUSIVE MODE;

DO $empty_core_guard$
BEGIN
    IF EXISTS (SELECT 1 FROM core.worlds) OR EXISTS (SELECT 1 FROM core.skills)
       OR EXISTS (SELECT 1 FROM core.templates) OR EXISTS (SELECT 1 FROM core.source_questions) THEN
        RAISE EXCEPTION 'Core already contains data. Import refused; existing rows are preserved. No reset is performed.';
    END IF;
END
$empty_core_guard$;

INSERT INTO core.worlds (world_id,name,database_name,dialect,schema_description,fk_relations,business_rules,planted_traps,allowed_sql_features) VALUES (
$world_world_id$enterprise_v1$world_world_id$,
$world_name$EnterpriseDB v1$world_name$,
$world_database_name$enterprise_db$world_database_name$,
$world_dialect$postgresql$world_dialect$,
$world_schema_description${
  "source": "Live PostgreSQL catalogs, read-only",
  "schema": "public",
  "catalog_sha256": "57e199fd63d3af2a1a7cd0684c6c12eec52606b5f0982ac0074d6569cc9d48c1",
  "tables": [
    {
      "schema": "public",
      "table": "categories",
      "columns": [
        {
          "name": "category_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "category_name",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "parent_category_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "description",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "text",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "is_active",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "boolean",
          "ordinal_position": 5,
          "default_expression": "true"
        }
      ],
      "primary_key": [
        "category_id"
      ],
      "constraints": [
        {
          "kind": "n",
          "name": "categories_category_id_not_null",
          "definition": "NOT NULL category_id",
          "table_name": "categories"
        },
        {
          "kind": "n",
          "name": "categories_category_name_not_null",
          "definition": "NOT NULL category_name",
          "table_name": "categories"
        },
        {
          "kind": "n",
          "name": "categories_is_active_not_null",
          "definition": "NOT NULL is_active",
          "table_name": "categories"
        },
        {
          "kind": "f",
          "name": "categories_parent_category_id_fkey",
          "definition": "FOREIGN KEY (parent_category_id) REFERENCES categories(category_id)",
          "table_name": "categories"
        },
        {
          "kind": "p",
          "name": "categories_pkey",
          "definition": "PRIMARY KEY (category_id)",
          "table_name": "categories"
        },
        {
          "kind": "c",
          "name": "chk_category_not_own_parent",
          "definition": "CHECK (((parent_category_id IS NULL) OR (parent_category_id <> category_id)))",
          "table_name": "categories"
        }
      ]
    },
    {
      "schema": "public",
      "table": "customer_addresses",
      "columns": [
        {
          "name": "address_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "customer_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "address_line",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(255)",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "city",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "district",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "postal_code",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "is_default",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "boolean",
          "ordinal_position": 7,
          "default_expression": "false"
        },
        {
          "name": "created_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 8,
          "default_expression": null
        }
      ],
      "primary_key": [
        "address_id"
      ],
      "constraints": [
        {
          "kind": "u",
          "name": "customer_addresses_address_id_customer_id_key",
          "definition": "UNIQUE (address_id, customer_id)",
          "table_name": "customer_addresses"
        },
        {
          "kind": "n",
          "name": "customer_addresses_address_id_not_null",
          "definition": "NOT NULL address_id",
          "table_name": "customer_addresses"
        },
        {
          "kind": "n",
          "name": "customer_addresses_address_line_not_null",
          "definition": "NOT NULL address_line",
          "table_name": "customer_addresses"
        },
        {
          "kind": "n",
          "name": "customer_addresses_city_not_null",
          "definition": "NOT NULL city",
          "table_name": "customer_addresses"
        },
        {
          "kind": "n",
          "name": "customer_addresses_created_at_not_null",
          "definition": "NOT NULL created_at",
          "table_name": "customer_addresses"
        },
        {
          "kind": "f",
          "name": "customer_addresses_customer_id_fkey",
          "definition": "FOREIGN KEY (customer_id) REFERENCES customers(customer_id)",
          "table_name": "customer_addresses"
        },
        {
          "kind": "n",
          "name": "customer_addresses_customer_id_not_null",
          "definition": "NOT NULL customer_id",
          "table_name": "customer_addresses"
        },
        {
          "kind": "n",
          "name": "customer_addresses_district_not_null",
          "definition": "NOT NULL district",
          "table_name": "customer_addresses"
        },
        {
          "kind": "n",
          "name": "customer_addresses_is_default_not_null",
          "definition": "NOT NULL is_default",
          "table_name": "customer_addresses"
        },
        {
          "kind": "p",
          "name": "customer_addresses_pkey",
          "definition": "PRIMARY KEY (address_id)",
          "table_name": "customer_addresses"
        }
      ]
    },
    {
      "schema": "public",
      "table": "customers",
      "columns": [
        {
          "name": "customer_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "full_name",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(150)",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "email",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(255)",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "phone",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "gender",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "date_of_birth",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "date",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "registered_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 7,
          "default_expression": null
        },
        {
          "name": "status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 8,
          "default_expression": null
        }
      ],
      "primary_key": [
        "customer_id"
      ],
      "constraints": [
        {
          "kind": "n",
          "name": "customers_customer_id_not_null",
          "definition": "NOT NULL customer_id",
          "table_name": "customers"
        },
        {
          "kind": "u",
          "name": "customers_email_key",
          "definition": "UNIQUE (email)",
          "table_name": "customers"
        },
        {
          "kind": "n",
          "name": "customers_email_not_null",
          "definition": "NOT NULL email",
          "table_name": "customers"
        },
        {
          "kind": "n",
          "name": "customers_full_name_not_null",
          "definition": "NOT NULL full_name",
          "table_name": "customers"
        },
        {
          "kind": "p",
          "name": "customers_pkey",
          "definition": "PRIMARY KEY (customer_id)",
          "table_name": "customers"
        },
        {
          "kind": "n",
          "name": "customers_registered_at_not_null",
          "definition": "NOT NULL registered_at",
          "table_name": "customers"
        },
        {
          "kind": "n",
          "name": "customers_status_not_null",
          "definition": "NOT NULL status",
          "table_name": "customers"
        }
      ]
    },
    {
      "schema": "public",
      "table": "departments",
      "columns": [
        {
          "name": "department_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "department_name",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(150)",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "manager_employee_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "created_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "date",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 5,
          "default_expression": null
        }
      ],
      "primary_key": [
        "department_id"
      ],
      "constraints": [
        {
          "kind": "n",
          "name": "departments_created_at_not_null",
          "definition": "NOT NULL created_at",
          "table_name": "departments"
        },
        {
          "kind": "n",
          "name": "departments_department_id_not_null",
          "definition": "NOT NULL department_id",
          "table_name": "departments"
        },
        {
          "kind": "n",
          "name": "departments_department_name_not_null",
          "definition": "NOT NULL department_name",
          "table_name": "departments"
        },
        {
          "kind": "p",
          "name": "departments_pkey",
          "definition": "PRIMARY KEY (department_id)",
          "table_name": "departments"
        },
        {
          "kind": "n",
          "name": "departments_status_not_null",
          "definition": "NOT NULL status",
          "table_name": "departments"
        },
        {
          "kind": "f",
          "name": "fk_departments_manager",
          "definition": "FOREIGN KEY (manager_employee_id) REFERENCES employees(employee_id)",
          "table_name": "departments"
        }
      ]
    },
    {
      "schema": "public",
      "table": "employees",
      "columns": [
        {
          "name": "employee_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "full_name",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(150)",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "department_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "manager_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "hire_date",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "date",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "job_title",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "current_salary",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 7,
          "default_expression": null
        },
        {
          "name": "status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 8,
          "default_expression": null
        }
      ],
      "primary_key": [
        "employee_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_employee_not_own_manager",
          "definition": "CHECK (((manager_id IS NULL) OR (manager_id <> employee_id)))",
          "table_name": "employees"
        },
        {
          "kind": "c",
          "name": "chk_employee_salary",
          "definition": "CHECK ((current_salary >= (0)::numeric))",
          "table_name": "employees"
        },
        {
          "kind": "n",
          "name": "employees_current_salary_not_null",
          "definition": "NOT NULL current_salary",
          "table_name": "employees"
        },
        {
          "kind": "f",
          "name": "employees_department_id_fkey",
          "definition": "FOREIGN KEY (department_id) REFERENCES departments(department_id)",
          "table_name": "employees"
        },
        {
          "kind": "n",
          "name": "employees_department_id_not_null",
          "definition": "NOT NULL department_id",
          "table_name": "employees"
        },
        {
          "kind": "n",
          "name": "employees_employee_id_not_null",
          "definition": "NOT NULL employee_id",
          "table_name": "employees"
        },
        {
          "kind": "n",
          "name": "employees_full_name_not_null",
          "definition": "NOT NULL full_name",
          "table_name": "employees"
        },
        {
          "kind": "n",
          "name": "employees_hire_date_not_null",
          "definition": "NOT NULL hire_date",
          "table_name": "employees"
        },
        {
          "kind": "n",
          "name": "employees_job_title_not_null",
          "definition": "NOT NULL job_title",
          "table_name": "employees"
        },
        {
          "kind": "f",
          "name": "employees_manager_id_fkey",
          "definition": "FOREIGN KEY (manager_id) REFERENCES employees(employee_id)",
          "table_name": "employees"
        },
        {
          "kind": "p",
          "name": "employees_pkey",
          "definition": "PRIMARY KEY (employee_id)",
          "table_name": "employees"
        },
        {
          "kind": "n",
          "name": "employees_status_not_null",
          "definition": "NOT NULL status",
          "table_name": "employees"
        }
      ]
    },
    {
      "schema": "public",
      "table": "inventory_transactions",
      "columns": [
        {
          "name": "transaction_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "product_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "warehouse_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "transaction_type",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(30)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "quantity_change",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "transaction_date",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "note",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "text",
          "ordinal_position": 9,
          "default_expression": null
        },
        {
          "name": "order_item_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 10,
          "default_expression": null
        }
      ],
      "primary_key": [
        "transaction_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_inventory_transaction",
          "definition": "CHECK (((((transaction_type)::text = 'import'::text) AND (quantity_change > 0) AND (order_item_id IS NULL)) OR (((transaction_type)::text = 'sale'::text) AND (quantity_change < 0) AND (order_item_id IS NOT NULL)) OR (((transaction_type)::text = 'return'::text) AND (quantity_change > 0) AND (order_item_id IS NOT NULL)) OR (((transaction_type)::text = 'adjustment'::text) AND (quantity_change <> 0) AND (order_item_id IS NULL))))",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "f",
          "name": "fk_inventory_order_item",
          "definition": "FOREIGN KEY (order_item_id) REFERENCES order_items(order_item_id)",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "p",
          "name": "inventory_transactions_pkey",
          "definition": "PRIMARY KEY (transaction_id)",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "f",
          "name": "inventory_transactions_product_id_fkey",
          "definition": "FOREIGN KEY (product_id) REFERENCES products(product_id)",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "n",
          "name": "inventory_transactions_product_id_not_null",
          "definition": "NOT NULL product_id",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "n",
          "name": "inventory_transactions_quantity_change_not_null",
          "definition": "NOT NULL quantity_change",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "n",
          "name": "inventory_transactions_transaction_date_not_null",
          "definition": "NOT NULL transaction_date",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "n",
          "name": "inventory_transactions_transaction_id_not_null",
          "definition": "NOT NULL transaction_id",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "n",
          "name": "inventory_transactions_transaction_type_not_null",
          "definition": "NOT NULL transaction_type",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "f",
          "name": "inventory_transactions_warehouse_id_fkey",
          "definition": "FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)",
          "table_name": "inventory_transactions"
        },
        {
          "kind": "n",
          "name": "inventory_transactions_warehouse_id_not_null",
          "definition": "NOT NULL warehouse_id",
          "table_name": "inventory_transactions"
        }
      ]
    },
    {
      "schema": "public",
      "table": "operating_expenses",
      "columns": [
        {
          "name": "expense_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "department_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "expense_category",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "amount",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "expense_date",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "date",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "description",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "text",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "approved_by_employee_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 7,
          "default_expression": null
        }
      ],
      "primary_key": [
        "expense_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_expense_amount",
          "definition": "CHECK ((amount >= (0)::numeric))",
          "table_name": "operating_expenses"
        },
        {
          "kind": "n",
          "name": "operating_expenses_amount_not_null",
          "definition": "NOT NULL amount",
          "table_name": "operating_expenses"
        },
        {
          "kind": "f",
          "name": "operating_expenses_approved_by_employee_id_fkey",
          "definition": "FOREIGN KEY (approved_by_employee_id) REFERENCES employees(employee_id)",
          "table_name": "operating_expenses"
        },
        {
          "kind": "f",
          "name": "operating_expenses_department_id_fkey",
          "definition": "FOREIGN KEY (department_id) REFERENCES departments(department_id)",
          "table_name": "operating_expenses"
        },
        {
          "kind": "n",
          "name": "operating_expenses_expense_category_not_null",
          "definition": "NOT NULL expense_category",
          "table_name": "operating_expenses"
        },
        {
          "kind": "n",
          "name": "operating_expenses_expense_date_not_null",
          "definition": "NOT NULL expense_date",
          "table_name": "operating_expenses"
        },
        {
          "kind": "n",
          "name": "operating_expenses_expense_id_not_null",
          "definition": "NOT NULL expense_id",
          "table_name": "operating_expenses"
        },
        {
          "kind": "p",
          "name": "operating_expenses_pkey",
          "definition": "PRIMARY KEY (expense_id)",
          "table_name": "operating_expenses"
        }
      ]
    },
    {
      "schema": "public",
      "table": "order_items",
      "columns": [
        {
          "name": "order_item_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "order_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "product_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "quantity",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "unit_price",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "discount_amount",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 6,
          "default_expression": "0"
        },
        {
          "name": "line_total",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 7,
          "default_expression": null
        }
      ],
      "primary_key": [
        "order_item_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_order_items_values",
          "definition": "CHECK (((quantity > 0) AND (unit_price >= (0)::numeric) AND (discount_amount >= (0)::numeric) AND (discount_amount <= ((quantity)::numeric * unit_price)) AND (line_total = (((quantity)::numeric * unit_price) - discount_amount))))",
          "table_name": "order_items"
        },
        {
          "kind": "n",
          "name": "order_items_discount_amount_not_null",
          "definition": "NOT NULL discount_amount",
          "table_name": "order_items"
        },
        {
          "kind": "n",
          "name": "order_items_line_total_not_null",
          "definition": "NOT NULL line_total",
          "table_name": "order_items"
        },
        {
          "kind": "f",
          "name": "order_items_order_id_fkey",
          "definition": "FOREIGN KEY (order_id) REFERENCES orders(order_id)",
          "table_name": "order_items"
        },
        {
          "kind": "n",
          "name": "order_items_order_id_not_null",
          "definition": "NOT NULL order_id",
          "table_name": "order_items"
        },
        {
          "kind": "n",
          "name": "order_items_order_item_id_not_null",
          "definition": "NOT NULL order_item_id",
          "table_name": "order_items"
        },
        {
          "kind": "p",
          "name": "order_items_pkey",
          "definition": "PRIMARY KEY (order_item_id)",
          "table_name": "order_items"
        },
        {
          "kind": "f",
          "name": "order_items_product_id_fkey",
          "definition": "FOREIGN KEY (product_id) REFERENCES products(product_id)",
          "table_name": "order_items"
        },
        {
          "kind": "n",
          "name": "order_items_product_id_not_null",
          "definition": "NOT NULL product_id",
          "table_name": "order_items"
        },
        {
          "kind": "n",
          "name": "order_items_quantity_not_null",
          "definition": "NOT NULL quantity",
          "table_name": "order_items"
        },
        {
          "kind": "n",
          "name": "order_items_unit_price_not_null",
          "definition": "NOT NULL unit_price",
          "table_name": "order_items"
        }
      ]
    },
    {
      "schema": "public",
      "table": "order_status_history",
      "columns": [
        {
          "name": "history_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "order_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "old_status",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(30)",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "new_status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(30)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "changed_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "changed_by_employee_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 6,
          "default_expression": null
        }
      ],
      "primary_key": [
        "history_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_order_history_status",
          "definition": "CHECK ((((old_status IS NULL) OR ((old_status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'shipped'::character varying, 'delivered'::character varying])::text[]))) AND ((new_status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'shipped'::character varying, 'delivered'::character varying, 'cancelled'::character varying])::text[]))))",
          "table_name": "order_status_history"
        },
        {
          "kind": "c",
          "name": "chk_order_history_transition",
          "definition": "CHECK ((((old_status IS NULL) AND ((new_status)::text = 'pending'::text)) OR (((old_status)::text = 'pending'::text) AND ((new_status)::text = ANY ((ARRAY['processing'::character varying, 'cancelled'::character varying])::text[]))) OR (((old_status)::text = 'processing'::text) AND ((new_status)::text = ANY ((ARRAY['shipped'::character varying, 'cancelled'::character varying])::text[]))) OR (((old_status)::text = 'shipped'::text) AND ((new_status)::text = 'delivered'::text))))",
          "table_name": "order_status_history"
        },
        {
          "kind": "n",
          "name": "order_status_history_changed_at_not_null",
          "definition": "NOT NULL changed_at",
          "table_name": "order_status_history"
        },
        {
          "kind": "f",
          "name": "order_status_history_changed_by_employee_id_fkey",
          "definition": "FOREIGN KEY (changed_by_employee_id) REFERENCES employees(employee_id)",
          "table_name": "order_status_history"
        },
        {
          "kind": "n",
          "name": "order_status_history_history_id_not_null",
          "definition": "NOT NULL history_id",
          "table_name": "order_status_history"
        },
        {
          "kind": "n",
          "name": "order_status_history_new_status_not_null",
          "definition": "NOT NULL new_status",
          "table_name": "order_status_history"
        },
        {
          "kind": "f",
          "name": "order_status_history_order_id_fkey",
          "definition": "FOREIGN KEY (order_id) REFERENCES orders(order_id)",
          "table_name": "order_status_history"
        },
        {
          "kind": "n",
          "name": "order_status_history_order_id_not_null",
          "definition": "NOT NULL order_id",
          "table_name": "order_status_history"
        },
        {
          "kind": "p",
          "name": "order_status_history_pkey",
          "definition": "PRIMARY KEY (history_id)",
          "table_name": "order_status_history"
        }
      ]
    },
    {
      "schema": "public",
      "table": "orders",
      "columns": [
        {
          "name": "order_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "customer_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "employee_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "shipping_address_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "warehouse_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "order_date",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(30)",
          "ordinal_position": 7,
          "default_expression": null
        },
        {
          "name": "total_amount",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 8,
          "default_expression": null
        },
        {
          "name": "shipping_fee",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 9,
          "default_expression": null
        },
        {
          "name": "carrier_name",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 10,
          "default_expression": null
        },
        {
          "name": "shipped_at",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 11,
          "default_expression": null
        },
        {
          "name": "delivered_at",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 12,
          "default_expression": null
        },
        {
          "name": "created_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 13,
          "default_expression": null
        }
      ],
      "primary_key": [
        "order_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_orders_amounts",
          "definition": "CHECK (((total_amount >= (0)::numeric) AND (shipping_fee >= (0)::numeric)))",
          "table_name": "orders"
        },
        {
          "kind": "c",
          "name": "chk_orders_status",
          "definition": "CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'shipped'::character varying, 'delivered'::character varying, 'cancelled'::character varying])::text[])))",
          "table_name": "orders"
        },
        {
          "kind": "c",
          "name": "chk_orders_timeline",
          "definition": "CHECK (((created_at <= order_date) AND ((shipped_at IS NULL) OR (shipped_at >= order_date)) AND ((delivered_at IS NULL) OR ((shipped_at IS NOT NULL) AND (delivered_at >= shipped_at)))))",
          "table_name": "orders"
        },
        {
          "kind": "f",
          "name": "fk_orders_shipping_address_customer",
          "definition": "FOREIGN KEY (shipping_address_id, customer_id) REFERENCES customer_addresses(address_id, customer_id)",
          "table_name": "orders"
        },
        {
          "kind": "n",
          "name": "orders_created_at_not_null",
          "definition": "NOT NULL created_at",
          "table_name": "orders"
        },
        {
          "kind": "f",
          "name": "orders_customer_id_fkey",
          "definition": "FOREIGN KEY (customer_id) REFERENCES customers(customer_id)",
          "table_name": "orders"
        },
        {
          "kind": "n",
          "name": "orders_customer_id_not_null",
          "definition": "NOT NULL customer_id",
          "table_name": "orders"
        },
        {
          "kind": "f",
          "name": "orders_employee_id_fkey",
          "definition": "FOREIGN KEY (employee_id) REFERENCES employees(employee_id)",
          "table_name": "orders"
        },
        {
          "kind": "n",
          "name": "orders_order_date_not_null",
          "definition": "NOT NULL order_date",
          "table_name": "orders"
        },
        {
          "kind": "n",
          "name": "orders_order_id_not_null",
          "definition": "NOT NULL order_id",
          "table_name": "orders"
        },
        {
          "kind": "p",
          "name": "orders_pkey",
          "definition": "PRIMARY KEY (order_id)",
          "table_name": "orders"
        },
        {
          "kind": "n",
          "name": "orders_shipping_address_id_not_null",
          "definition": "NOT NULL shipping_address_id",
          "table_name": "orders"
        },
        {
          "kind": "n",
          "name": "orders_shipping_fee_not_null",
          "definition": "NOT NULL shipping_fee",
          "table_name": "orders"
        },
        {
          "kind": "n",
          "name": "orders_status_not_null",
          "definition": "NOT NULL status",
          "table_name": "orders"
        },
        {
          "kind": "n",
          "name": "orders_total_amount_not_null",
          "definition": "NOT NULL total_amount",
          "table_name": "orders"
        },
        {
          "kind": "f",
          "name": "orders_warehouse_id_fkey",
          "definition": "FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)",
          "table_name": "orders"
        }
      ]
    },
    {
      "schema": "public",
      "table": "payments",
      "columns": [
        {
          "name": "payment_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "order_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "amount",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "payment_method",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(30)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "payment_status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(30)",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "attempted_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "transaction_code",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 8,
          "default_expression": null
        }
      ],
      "primary_key": [
        "payment_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_payment_amount",
          "definition": "CHECK ((amount > (0)::numeric))",
          "table_name": "payments"
        },
        {
          "kind": "c",
          "name": "chk_payment_status",
          "definition": "CHECK (((payment_status)::text = ANY ((ARRAY['success'::character varying, 'failed'::character varying])::text[])))",
          "table_name": "payments"
        },
        {
          "kind": "n",
          "name": "payments_amount_not_null",
          "definition": "NOT NULL amount",
          "table_name": "payments"
        },
        {
          "kind": "n",
          "name": "payments_attempted_at_not_null",
          "definition": "NOT NULL attempted_at",
          "table_name": "payments"
        },
        {
          "kind": "f",
          "name": "payments_order_id_fkey",
          "definition": "FOREIGN KEY (order_id) REFERENCES orders(order_id)",
          "table_name": "payments"
        },
        {
          "kind": "n",
          "name": "payments_order_id_not_null",
          "definition": "NOT NULL order_id",
          "table_name": "payments"
        },
        {
          "kind": "n",
          "name": "payments_payment_id_not_null",
          "definition": "NOT NULL payment_id",
          "table_name": "payments"
        },
        {
          "kind": "n",
          "name": "payments_payment_method_not_null",
          "definition": "NOT NULL payment_method",
          "table_name": "payments"
        },
        {
          "kind": "n",
          "name": "payments_payment_status_not_null",
          "definition": "NOT NULL payment_status",
          "table_name": "payments"
        },
        {
          "kind": "p",
          "name": "payments_pkey",
          "definition": "PRIMARY KEY (payment_id)",
          "table_name": "payments"
        }
      ]
    },
    {
      "schema": "public",
      "table": "products",
      "columns": [
        {
          "name": "product_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "product_name",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(200)",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "category_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "supplier_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "sku",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(50)",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "list_price",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "cost_price",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 7,
          "default_expression": null
        },
        {
          "name": "created_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 8,
          "default_expression": null
        },
        {
          "name": "is_active",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "boolean",
          "ordinal_position": 9,
          "default_expression": "true"
        }
      ],
      "primary_key": [
        "product_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_product_prices",
          "definition": "CHECK (((list_price >= (0)::numeric) AND (cost_price >= (0)::numeric)))",
          "table_name": "products"
        },
        {
          "kind": "f",
          "name": "products_category_id_fkey",
          "definition": "FOREIGN KEY (category_id) REFERENCES categories(category_id)",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_category_id_not_null",
          "definition": "NOT NULL category_id",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_cost_price_not_null",
          "definition": "NOT NULL cost_price",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_created_at_not_null",
          "definition": "NOT NULL created_at",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_is_active_not_null",
          "definition": "NOT NULL is_active",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_list_price_not_null",
          "definition": "NOT NULL list_price",
          "table_name": "products"
        },
        {
          "kind": "p",
          "name": "products_pkey",
          "definition": "PRIMARY KEY (product_id)",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_product_id_not_null",
          "definition": "NOT NULL product_id",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_product_name_not_null",
          "definition": "NOT NULL product_name",
          "table_name": "products"
        },
        {
          "kind": "u",
          "name": "products_sku_key",
          "definition": "UNIQUE (sku)",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_sku_not_null",
          "definition": "NOT NULL sku",
          "table_name": "products"
        },
        {
          "kind": "f",
          "name": "products_supplier_id_fkey",
          "definition": "FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)",
          "table_name": "products"
        },
        {
          "kind": "n",
          "name": "products_supplier_id_not_null",
          "definition": "NOT NULL supplier_id",
          "table_name": "products"
        }
      ]
    },
    {
      "schema": "public",
      "table": "refunds",
      "columns": [
        {
          "name": "refund_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "payment_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "refund_amount",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "refund_reason",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(150)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "refund_status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(30)",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "requested_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "completed_at",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "timestamp without time zone",
          "ordinal_position": 7,
          "default_expression": null
        }
      ],
      "primary_key": [
        "refund_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_refund_amount",
          "definition": "CHECK ((refund_amount > (0)::numeric))",
          "table_name": "refunds"
        },
        {
          "kind": "c",
          "name": "chk_refund_timeline",
          "definition": "CHECK (((completed_at IS NULL) OR (completed_at >= requested_at)))",
          "table_name": "refunds"
        },
        {
          "kind": "f",
          "name": "refunds_payment_id_fkey",
          "definition": "FOREIGN KEY (payment_id) REFERENCES payments(payment_id)",
          "table_name": "refunds"
        },
        {
          "kind": "n",
          "name": "refunds_payment_id_not_null",
          "definition": "NOT NULL payment_id",
          "table_name": "refunds"
        },
        {
          "kind": "p",
          "name": "refunds_pkey",
          "definition": "PRIMARY KEY (refund_id)",
          "table_name": "refunds"
        },
        {
          "kind": "n",
          "name": "refunds_refund_amount_not_null",
          "definition": "NOT NULL refund_amount",
          "table_name": "refunds"
        },
        {
          "kind": "n",
          "name": "refunds_refund_id_not_null",
          "definition": "NOT NULL refund_id",
          "table_name": "refunds"
        },
        {
          "kind": "n",
          "name": "refunds_refund_reason_not_null",
          "definition": "NOT NULL refund_reason",
          "table_name": "refunds"
        },
        {
          "kind": "n",
          "name": "refunds_refund_status_not_null",
          "definition": "NOT NULL refund_status",
          "table_name": "refunds"
        },
        {
          "kind": "n",
          "name": "refunds_requested_at_not_null",
          "definition": "NOT NULL requested_at",
          "table_name": "refunds"
        }
      ]
    },
    {
      "schema": "public",
      "table": "salary_history",
      "columns": [
        {
          "name": "salary_history_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "employee_id",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "salary",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "numeric(15,2)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "effective_date",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "date",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "change_reason",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(150)",
          "ordinal_position": 6,
          "default_expression": null
        }
      ],
      "primary_key": [
        "salary_history_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_salary_history_positive",
          "definition": "CHECK ((salary > (0)::numeric))",
          "table_name": "salary_history"
        },
        {
          "kind": "n",
          "name": "salary_history_change_reason_not_null",
          "definition": "NOT NULL change_reason",
          "table_name": "salary_history"
        },
        {
          "kind": "n",
          "name": "salary_history_effective_date_not_null",
          "definition": "NOT NULL effective_date",
          "table_name": "salary_history"
        },
        {
          "kind": "f",
          "name": "salary_history_employee_id_fkey",
          "definition": "FOREIGN KEY (employee_id) REFERENCES employees(employee_id)",
          "table_name": "salary_history"
        },
        {
          "kind": "n",
          "name": "salary_history_employee_id_not_null",
          "definition": "NOT NULL employee_id",
          "table_name": "salary_history"
        },
        {
          "kind": "n",
          "name": "salary_history_new_salary_not_null",
          "definition": "NOT NULL salary",
          "table_name": "salary_history"
        },
        {
          "kind": "p",
          "name": "salary_history_pkey",
          "definition": "PRIMARY KEY (salary_history_id)",
          "table_name": "salary_history"
        },
        {
          "kind": "n",
          "name": "salary_history_salary_history_id_not_null",
          "definition": "NOT NULL salary_history_id",
          "table_name": "salary_history"
        },
        {
          "kind": "u",
          "name": "uq_salary_history_employee_date",
          "definition": "UNIQUE (employee_id, effective_date)",
          "table_name": "salary_history"
        }
      ]
    },
    {
      "schema": "public",
      "table": "suppliers",
      "columns": [
        {
          "name": "supplier_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "supplier_name",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(150)",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "contact_email",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(255)",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "phone",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "country",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "joined_at",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "date",
          "ordinal_position": 6,
          "default_expression": null
        },
        {
          "name": "status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 7,
          "default_expression": null
        }
      ],
      "primary_key": [
        "supplier_id"
      ],
      "constraints": [
        {
          "kind": "n",
          "name": "suppliers_joined_at_not_null",
          "definition": "NOT NULL joined_at",
          "table_name": "suppliers"
        },
        {
          "kind": "p",
          "name": "suppliers_pkey",
          "definition": "PRIMARY KEY (supplier_id)",
          "table_name": "suppliers"
        },
        {
          "kind": "n",
          "name": "suppliers_status_not_null",
          "definition": "NOT NULL status",
          "table_name": "suppliers"
        },
        {
          "kind": "n",
          "name": "suppliers_supplier_id_not_null",
          "definition": "NOT NULL supplier_id",
          "table_name": "suppliers"
        },
        {
          "kind": "n",
          "name": "suppliers_supplier_name_not_null",
          "definition": "NOT NULL supplier_name",
          "table_name": "suppliers"
        }
      ]
    },
    {
      "schema": "public",
      "table": "warehouses",
      "columns": [
        {
          "name": "warehouse_id",
          "identity": "d",
          "nullable": false,
          "primary_key": true,
          "postgres_type": "integer",
          "ordinal_position": 1,
          "default_expression": null
        },
        {
          "name": "warehouse_name",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(150)",
          "ordinal_position": 2,
          "default_expression": null
        },
        {
          "name": "city",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(100)",
          "ordinal_position": 3,
          "default_expression": null
        },
        {
          "name": "capacity",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 4,
          "default_expression": null
        },
        {
          "name": "manager_employee_id",
          "identity": "",
          "nullable": true,
          "primary_key": false,
          "postgres_type": "integer",
          "ordinal_position": 5,
          "default_expression": null
        },
        {
          "name": "status",
          "identity": "",
          "nullable": false,
          "primary_key": false,
          "postgres_type": "character varying(20)",
          "ordinal_position": 6,
          "default_expression": null
        }
      ],
      "primary_key": [
        "warehouse_id"
      ],
      "constraints": [
        {
          "kind": "c",
          "name": "chk_warehouse_capacity",
          "definition": "CHECK ((capacity >= 0))",
          "table_name": "warehouses"
        },
        {
          "kind": "n",
          "name": "warehouses_capacity_not_null",
          "definition": "NOT NULL capacity",
          "table_name": "warehouses"
        },
        {
          "kind": "n",
          "name": "warehouses_city_not_null",
          "definition": "NOT NULL city",
          "table_name": "warehouses"
        },
        {
          "kind": "f",
          "name": "warehouses_manager_employee_id_fkey",
          "definition": "FOREIGN KEY (manager_employee_id) REFERENCES employees(employee_id)",
          "table_name": "warehouses"
        },
        {
          "kind": "p",
          "name": "warehouses_pkey",
          "definition": "PRIMARY KEY (warehouse_id)",
          "table_name": "warehouses"
        },
        {
          "kind": "n",
          "name": "warehouses_status_not_null",
          "definition": "NOT NULL status",
          "table_name": "warehouses"
        },
        {
          "kind": "n",
          "name": "warehouses_warehouse_id_not_null",
          "definition": "NOT NULL warehouse_id",
          "table_name": "warehouses"
        },
        {
          "kind": "n",
          "name": "warehouses_warehouse_name_not_null",
          "definition": "NOT NULL warehouse_name",
          "table_name": "warehouses"
        }
      ]
    }
  ]
}$world_schema_description$::jsonb,
$world_fk_relations$[
  {
    "name": "categories_parent_category_id_fkey",
    "columns": [
      "parent_category_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (parent_category_id) REFERENCES categories(category_id)",
    "table_name": "categories",
    "referenced_table": "categories",
    "referenced_schema": "public",
    "referenced_columns": [
      "category_id"
    ]
  },
  {
    "name": "customer_addresses_customer_id_fkey",
    "columns": [
      "customer_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (customer_id) REFERENCES customers(customer_id)",
    "table_name": "customer_addresses",
    "referenced_table": "customers",
    "referenced_schema": "public",
    "referenced_columns": [
      "customer_id"
    ]
  },
  {
    "name": "fk_departments_manager",
    "columns": [
      "manager_employee_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (manager_employee_id) REFERENCES employees(employee_id)",
    "table_name": "departments",
    "referenced_table": "employees",
    "referenced_schema": "public",
    "referenced_columns": [
      "employee_id"
    ]
  },
  {
    "name": "employees_department_id_fkey",
    "columns": [
      "department_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (department_id) REFERENCES departments(department_id)",
    "table_name": "employees",
    "referenced_table": "departments",
    "referenced_schema": "public",
    "referenced_columns": [
      "department_id"
    ]
  },
  {
    "name": "employees_manager_id_fkey",
    "columns": [
      "manager_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (manager_id) REFERENCES employees(employee_id)",
    "table_name": "employees",
    "referenced_table": "employees",
    "referenced_schema": "public",
    "referenced_columns": [
      "employee_id"
    ]
  },
  {
    "name": "fk_inventory_order_item",
    "columns": [
      "order_item_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (order_item_id) REFERENCES order_items(order_item_id)",
    "table_name": "inventory_transactions",
    "referenced_table": "order_items",
    "referenced_schema": "public",
    "referenced_columns": [
      "order_item_id"
    ]
  },
  {
    "name": "inventory_transactions_product_id_fkey",
    "columns": [
      "product_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (product_id) REFERENCES products(product_id)",
    "table_name": "inventory_transactions",
    "referenced_table": "products",
    "referenced_schema": "public",
    "referenced_columns": [
      "product_id"
    ]
  },
  {
    "name": "inventory_transactions_warehouse_id_fkey",
    "columns": [
      "warehouse_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)",
    "table_name": "inventory_transactions",
    "referenced_table": "warehouses",
    "referenced_schema": "public",
    "referenced_columns": [
      "warehouse_id"
    ]
  },
  {
    "name": "operating_expenses_approved_by_employee_id_fkey",
    "columns": [
      "approved_by_employee_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (approved_by_employee_id) REFERENCES employees(employee_id)",
    "table_name": "operating_expenses",
    "referenced_table": "employees",
    "referenced_schema": "public",
    "referenced_columns": [
      "employee_id"
    ]
  },
  {
    "name": "operating_expenses_department_id_fkey",
    "columns": [
      "department_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (department_id) REFERENCES departments(department_id)",
    "table_name": "operating_expenses",
    "referenced_table": "departments",
    "referenced_schema": "public",
    "referenced_columns": [
      "department_id"
    ]
  },
  {
    "name": "order_items_order_id_fkey",
    "columns": [
      "order_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (order_id) REFERENCES orders(order_id)",
    "table_name": "order_items",
    "referenced_table": "orders",
    "referenced_schema": "public",
    "referenced_columns": [
      "order_id"
    ]
  },
  {
    "name": "order_items_product_id_fkey",
    "columns": [
      "product_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (product_id) REFERENCES products(product_id)",
    "table_name": "order_items",
    "referenced_table": "products",
    "referenced_schema": "public",
    "referenced_columns": [
      "product_id"
    ]
  },
  {
    "name": "order_status_history_changed_by_employee_id_fkey",
    "columns": [
      "changed_by_employee_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (changed_by_employee_id) REFERENCES employees(employee_id)",
    "table_name": "order_status_history",
    "referenced_table": "employees",
    "referenced_schema": "public",
    "referenced_columns": [
      "employee_id"
    ]
  },
  {
    "name": "order_status_history_order_id_fkey",
    "columns": [
      "order_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (order_id) REFERENCES orders(order_id)",
    "table_name": "order_status_history",
    "referenced_table": "orders",
    "referenced_schema": "public",
    "referenced_columns": [
      "order_id"
    ]
  },
  {
    "name": "fk_orders_shipping_address_customer",
    "columns": [
      "shipping_address_id",
      "customer_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (shipping_address_id, customer_id) REFERENCES customer_addresses(address_id, customer_id)",
    "table_name": "orders",
    "referenced_table": "customer_addresses",
    "referenced_schema": "public",
    "referenced_columns": [
      "address_id",
      "customer_id"
    ]
  },
  {
    "name": "orders_customer_id_fkey",
    "columns": [
      "customer_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (customer_id) REFERENCES customers(customer_id)",
    "table_name": "orders",
    "referenced_table": "customers",
    "referenced_schema": "public",
    "referenced_columns": [
      "customer_id"
    ]
  },
  {
    "name": "orders_employee_id_fkey",
    "columns": [
      "employee_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (employee_id) REFERENCES employees(employee_id)",
    "table_name": "orders",
    "referenced_table": "employees",
    "referenced_schema": "public",
    "referenced_columns": [
      "employee_id"
    ]
  },
  {
    "name": "orders_warehouse_id_fkey",
    "columns": [
      "warehouse_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)",
    "table_name": "orders",
    "referenced_table": "warehouses",
    "referenced_schema": "public",
    "referenced_columns": [
      "warehouse_id"
    ]
  },
  {
    "name": "payments_order_id_fkey",
    "columns": [
      "order_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (order_id) REFERENCES orders(order_id)",
    "table_name": "payments",
    "referenced_table": "orders",
    "referenced_schema": "public",
    "referenced_columns": [
      "order_id"
    ]
  },
  {
    "name": "products_category_id_fkey",
    "columns": [
      "category_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (category_id) REFERENCES categories(category_id)",
    "table_name": "products",
    "referenced_table": "categories",
    "referenced_schema": "public",
    "referenced_columns": [
      "category_id"
    ]
  },
  {
    "name": "products_supplier_id_fkey",
    "columns": [
      "supplier_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)",
    "table_name": "products",
    "referenced_table": "suppliers",
    "referenced_schema": "public",
    "referenced_columns": [
      "supplier_id"
    ]
  },
  {
    "name": "refunds_payment_id_fkey",
    "columns": [
      "payment_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (payment_id) REFERENCES payments(payment_id)",
    "table_name": "refunds",
    "referenced_table": "payments",
    "referenced_schema": "public",
    "referenced_columns": [
      "payment_id"
    ]
  },
  {
    "name": "salary_history_employee_id_fkey",
    "columns": [
      "employee_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (employee_id) REFERENCES employees(employee_id)",
    "table_name": "salary_history",
    "referenced_table": "employees",
    "referenced_schema": "public",
    "referenced_columns": [
      "employee_id"
    ]
  },
  {
    "name": "warehouses_manager_employee_id_fkey",
    "columns": [
      "manager_employee_id"
    ],
    "validated": true,
    "definition": "FOREIGN KEY (manager_employee_id) REFERENCES employees(employee_id)",
    "table_name": "warehouses",
    "referenced_table": "employees",
    "referenced_schema": "public",
    "referenced_columns": [
      "employee_id"
    ]
  }
]$world_fk_relations$::jsonb,
$world_business_rules${
  "sources": [
    {
      "path": "rang_buoc.docx",
      "sha256": "a1d4df7a8036a4836f7a06af781fdf9729c69a7fd14085006c492ef44e259f1e"
    },
    {
      "path": "postgre/enterprise_db/validate_enterprisedb_br01_br16.sql",
      "sha256": "f253afd3cef9176ee149905c597bd87ee0b0d2a07bb35e1abf1ca4ed520d9aa3"
    },
    {
      "path": "Schema database.docx",
      "sha256": "b28943284f62635a2df721de01af869da1adcec86e2af9a47ca9c526b4b8c305"
    }
  ],
  "rules": [
    {
      "code": "BR01",
      "title_from_document": "BR01 — Khách hàng phải đăng ký trước khi đặt hàng",
      "document_excerpt": "BR01 — Khách hàng phải đăng ký trước khi đặt hàng\nBảng liên quan: customers, orders\nBảng\nTrường\nVai trò\ncustomers\ncustomer_id\nXác định khách hàng\ncustomers\nregistered_at\nThời điểm đăng ký\norders\ncustomer_id\nXác định người đặt đơn\norders\norder_date\nThời điểm đặt hàng\nĐiều kiện ràng buộc:\nVới mỗi đơn hàng, phải đảm bảo:\norders.order_date >= customers.registered_at\nVí dụ:\nKhách hàng\nNgày đăng ký\nNgày đặt hàng\nKết quả\nKH01\n01/01/2025\n15/02/2025\nHợp lệ\nKH02\n10/03/2025\n01/02/2025\nKhông hợp lệ\nVì sao cần? Nếu Python tạo đơn hàng ngẫu nhiên mà không dựa vào ngày đăng ký, sẽ xuất hiện đơn hàng trước khi khách hàng có tài khoản.\nĐây là quy tắc bổ sung đề xuất, giả định mọi đơn hàng đều được tạo sau khi khách đăng ký.\nB. Sales & Orders",
      "dataset_v1_validator_excerpt": "-- BR01: Order placed after customer registration.\nINSERT INTO br_validation_violations\nSELECT 'BR01','order_before_registration',o.order_id::text,\n       jsonb_build_object('order_date',o.order_date,'registered_at',c.registered_at)\nFROM orders o JOIN customers c USING(customer_id)\nWHERE o.order_date < c.registered_at;"
    },
    {
      "code": "BR02",
      "title_from_document": "BR02 — Tổng tiền đơn hàng phải khớp chi tiết đơn hàng",
      "document_excerpt": "BR02 — Tổng tiền đơn hàng phải khớp chi tiết đơn hàng\nBảng liên quan: orders, order_items\nBảng\nTrường\nVai trò\norders\norder_id\nXác định đơn hàng\norders\ntotal_amount\nTổng tiền đơn\norders\nshipping_fee\nPhí vận chuyển\norder_items\norder_id\nCác dòng thuộc đơn\norder_items\nline_total\nThành tiền từng dòng\nĐiều kiện:\n\\[ \\text{total\\_amount}=\\sum \\text{line\\_total}+\\text{shipping\\_fee} \\]\nVí dụ đơn hàng #1001:\nKhoản\nSố tiền\nSản phẩm A\n200.000đ\nSản phẩm B\n300.000đ\nPhí vận chuyển\n30.000đ\nTổng đúng\n530.000đ\nNếu orders.total_amount = 600.000 thì dữ liệu sai, dù tất cả FK đều hợp lệ.\nPython cần làm gì? Sinh order_items trước về mặt logic, tính tổng từ các dòng hàng, sau đó gán giá trị chính xác cho orders.total_amount. Thứ tự INSERT vật lý vẫn có thể là orders rồi order_items.",
      "dataset_v1_validator_excerpt": "-- BR02: Each order has at least one line; total includes shipping fee.\nINSERT INTO br_validation_violations\nSELECT 'BR02','order_total_or_missing_items',o.order_id::text,\n       jsonb_build_object('total_amount',o.total_amount,'expected',COALESCE(x.items_total,0)+o.shipping_fee,'item_count',COALESCE(x.item_count,0))\nFROM orders o LEFT JOIN (\n SELECT order_id, SUM(line_total) items_total, COUNT(*) item_count\n FROM order_items GROUP BY order_id\n) x USING(order_id)\nWHERE COALESCE(x.item_count,0)=0 OR o.total_amount IS DISTINCT FROM (COALESCE(x.items_total,0)+o.shipping_fee);"
    },
    {
      "code": "BR03",
      "title_from_document": "BR03 — Trạng thái đơn hàng phải khớp lịch sử(hỏi lại phần có 2 trạng thái ở bảng history; hỏi về vấn đề: cần thống nhất những chuyển trạng thái nào được phép. Đây là chính sách chưa được xác định đầy đủ trong schema)",
      "document_excerpt": "BR03 — Trạng thái đơn hàng phải khớp lịch sử(hỏi lại phần có 2 trạng thái ở bảng history; hỏi về vấn đề: cần thống nhất những chuyển trạng thái nào được phép. Đây là chính sách chưa được xác định đầy đủ trong schema)\nVÒNG ĐỜI ĐƠN HÀNG — VÍ DỤ ĐỀ XUẤT\npending\nChờ xử lý\nprocessing\nĐang xử lý\nshipped\nĐã gửi hàng\ndelivered\nĐã giao thành công ; Nhánh hủy: pending → cancelled hoặc processing → cancelled \n\nBảng liên quan: orders, order_status_history\nBảng\nTrường\norders\norder_id, status\norder_status_history\norder_id, old_status, new_status, changed_at, history_id\nĐiều kiện:\nTrạng thái mới của một lần thay đổi phải bằng trạng thái cũ của lần tiếp theo.\nCác sự kiện phải được sắp xếp theo changed_at, rồi history_id khi trùng thời điểm.\nTrạng thái mới của sự kiện cuối cùng phải bằng orders.status.\nVí dụ hợp lệ:\npending\nprocessing\nshipped\norders.status = 'shipped'\nNếu lịch sử cuối là shipped nhưng orders.status = 'delivered', dữ liệu không nhất quán.\nNgoài ra, cần thống nhất những chuyển trạng thái nào được phép. Đây là chính sách chưa được xác định đầy đủ trong schema.",
      "dataset_v1_validator_excerpt": "-- BR03: Every order starts at pending, history links continuously,\n-- legal transitions only, last status equals orders.status.\nWITH h AS (\n SELECT osh.*,\n        ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY changed_at,history_id) rn,\n        LAG(new_status) OVER(PARTITION BY order_id ORDER BY changed_at,history_id) prev_status,\n        LEAD(history_id) OVER(PARTITION BY order_id ORDER BY changed_at,history_id) next_id\n FROM order_status_history osh\n)\nINSERT INTO br_validation_violations\nSELECT 'BR03','invalid_status_history_event',history_id::text,\n       jsonb_build_object('order_id',order_id,'old',old_status,'new',new_status,'previous',prev_status,'position',rn)\nFROM h WHERE\n (rn=1 AND (old_status IS NOT NULL OR new_status <> 'pending'))\n OR (rn>1 AND old_status IS DISTINCT FROM prev_status)\n OR NOT ( (old_status IS NULL AND new_status='pending')\n       OR (old_status='pending' AND new_status IN ('processing','cancelled'))\n       OR (old_status='processing' AND new_status IN ('shipped','cancelled'))\n       OR (old_status='shipped' AND new_status='delivered') );\n\nWITH last_h AS (\n SELECT order_id,new_status, ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY changed_at DESC,history_id DESC) rn\n FROM order_status_history\n)\nINSERT INTO br_validation_violations\nSELECT 'BR03','missing_or_mismatched_final_status',o.order_id::text,\n       jsonb_build_object('order_status',o.status,'last_history_status',h.new_status)\nFROM orders o LEFT JOIN last_h h ON h.order_id=o.order_id AND h.rn=1\nWHERE h.order_id IS NULL OR o.status IS DISTINCT FROM h.new_status\n   OR o.status NOT IN ('pending','processing','shipped','delivered','cancelled');"
    },
    {
      "code": "BR04",
      "title_from_document": "BR04 — Thời gian xử lý và giao hàng hợp lý(Xử lý vụ thời điểm đặt hàng và thời điểm tạo bản ghi)",
      "document_excerpt": "BR04 — Thời gian xử lý và giao hàng hợp lý(Xử lý vụ thời điểm đặt hàng và thời điểm tạo bản ghi)\nBảng liên quan: orders, order_status_history\nTrường liên quan:\norders.created_at\norders.order_date\norders.shipped_at\norders.delivered_at\norder_status_history.changed_at\nĐiều kiện đề xuất:\n\\[ created\\_at \\le order\\_date \\le shipped\\_at \\le delivered\\_at \\]\nChỉ so sánh các thời điểm giao nhận khi chúng có giá trị.\nNgoài ra, thời điểm thay đổi trạng thái phải phù hợp với vòng đời đơn hàng. Ví dụ, không thể có sự kiện giao hàng trước khi đặt hàng.\nMột đơn đang xử lý có thể có shipped_at = NULL và delivered_at = NULL; điều này hợp lệ.\nC. Product & Inventory",
      "dataset_v1_validator_excerpt": "-- BR04: Order timestamps and event timeline.\nINSERT INTO br_validation_violations\nSELECT 'BR04','invalid_order_timeline',o.order_id::text,\n       jsonb_build_object('created_at',created_at,'order_date',order_date,'shipped_at',shipped_at,'delivered_at',delivered_at,'status',status)\nFROM orders o\nWHERE created_at > order_date\n   OR (shipped_at IS NOT NULL AND shipped_at < order_date)\n   OR (delivered_at IS NOT NULL AND (shipped_at IS NULL OR delivered_at < shipped_at))\n   OR (status IN ('shipped','delivered') AND shipped_at IS NULL)\n   OR (status='delivered' AND delivered_at IS NULL)\n   OR (status IN ('pending','processing','cancelled') AND delivered_at IS NOT NULL);\n\nINSERT INTO br_validation_violations\nSELECT 'BR04','status_event_before_order',h.history_id::text,\n       jsonb_build_object('order_id',h.order_id,'changed_at',h.changed_at,'order_date',o.order_date)\nFROM order_status_history h JOIN orders o USING(order_id)\nWHERE h.changed_at < o.order_date;"
    },
    {
      "code": "BR05",
      "title_from_document": "BR05 — Tồn kho không được âm",
      "document_excerpt": "BR05 — Tồn kho không được âm\nBảng liên quan: inventory_transactions, products, warehouses.\nTrong đó, products và warehouses xác định sản phẩm và kho; số lượng tồn thực tế được tính từ inventory_transactions.\nTrường quan trọng:\nproduct_id\nwarehouse_id\nquantity_change\ntransaction_date\ntransaction_id\nĐiều kiện:\nVới mỗi cặp (product_id, warehouse_id), tổng tích lũy quantity_change phải luôn lớn hơn hoặc bằng 0.\nVí dụ:\nGiao dịch\nThay đổi\nTồn sau giao dịch\nNhập kho\n+100\n100\nBán hàng\n-30\n70\nBán hàng\n-80\n-10\nGiao dịch cuối không hợp lệ.\nĐiểm quan trọng: không chỉ kiểm tra tồn kho cuối cùng, mà phải kiểm tra tồn sau từng giao dịch theo thứ tự thời gian.",
      "dataset_v1_validator_excerpt": "-- BR05: Running stock for each product + warehouse (tie break by transaction_id).\nWITH running AS (\n SELECT transaction_id,product_id,warehouse_id,transaction_date,\n        SUM(quantity_change) OVER(PARTITION BY product_id,warehouse_id ORDER BY transaction_date,transaction_id ROWS UNBOUNDED PRECEDING) stock_after\n FROM inventory_transactions\n)\nINSERT INTO br_validation_violations\nSELECT 'BR05','negative_running_stock',transaction_id::text,\n       jsonb_build_object('product_id',product_id,'warehouse_id',warehouse_id,'stock_after',stock_after)\nFROM running WHERE stock_after < 0;"
    },
    {
      "code": "BR06",
      "title_from_document": "BR06 — Không vượt sức chứa kho",
      "document_excerpt": "BR06 — Không vượt sức chứa kho\nBảng liên quan: warehouses, inventory_transactions\nBảng\nTrường\nwarehouses\nwarehouse_id, capacity\ninventory_transactions\nwarehouse_id, product_id, quantity_change, transaction_date\nĐiều kiện:\n\\[ \\sum_{\\text{mọi sản phẩm trong kho}}\\text{tồn hiện tại}\\le \\text{capacity} \\]\nVí dụ kho A có sức chứa 500 đơn vị:\nSản phẩm X: 200.\nSản phẩm Y: 150.\nSản phẩm Z: 100.\nTổng là 450, hợp lệ. Nếu nhập thêm 100 đơn vị thì tổng thành 550, không hợp lệ.\nCũng như BR05, quy tắc này cần đúng ở mọi thời điểm giao dịch, không chỉ cuối kỳ.",
      "dataset_v1_validator_excerpt": "-- BR06: Aggregate warehouse stock at EACH transaction event, not only final.\n-- Assumes inventory ordering is (transaction_date,transaction_id).\nWITH events AS (\n SELECT t.transaction_id,t.warehouse_id,t.transaction_date,w.capacity,\n        SUM(t.quantity_change) OVER(PARTITION BY t.warehouse_id ORDER BY t.transaction_date,t.transaction_id ROWS UNBOUNDED PRECEDING) warehouse_stock\n FROM inventory_transactions t JOIN warehouses w USING(warehouse_id)\n)\nINSERT INTO br_validation_violations\nSELECT 'BR06','warehouse_capacity_exceeded',transaction_id::text,\n       jsonb_build_object('warehouse_id',warehouse_id,'warehouse_stock',warehouse_stock,'capacity',capacity)\nFROM events WHERE warehouse_stock > capacity;"
    },
    {
      "code": "BR07",
      "title_from_document": "BR07 — Giao dịch xuất kho và trả hàng phải khớp với đơn hàng",
      "document_excerpt": "BR07 — Giao dịch xuất kho và trả hàng phải khớp với đơn hàng\nBảng liên quan: orders, order_items, inventory_transactions, warehouses\nQuy ước nghiệp vụ:\ntransaction_type gồm 4 giá trị: import, sale, return, adjustment.\nMỗi đơn hàng chỉ xuất hàng từ một kho duy nhất.\nMỗi dòng sản phẩm trong đơn hàng chỉ được xuất một lần, không chia thành nhiều đợt.\nKhi trả hàng, khách phải trả toàn bộ sản phẩm trong đơn, không hỗ trợ trả một phần.\nMọi sản phẩm đều được tính theo đơn vị số lượng nguyên, mỗi sản phẩm chiếm một đơn vị sức chứa kho.\nBỏ hai trường reference_type, reference_id trong inventory_transactions, thay bằng order_item_id (FK đến order_items, cho phép NULL).\nCác trường liên quan:\nBảng\nTrường\norders\norder_id, warehouse_id, status\norder_items\norder_item_id, order_id, product_id, quantity\ninventory_transactions\ntransaction_id, order_item_id, product_id, warehouse_id, transaction_type, quantity_change, transaction_date\nwarehouses\nwarehouse_id, capacity\nĐiều kiện nghiệp vụ:\n1. Đối với sale (xuất bán):\norder_item_id bắt buộc có giá trị và phải tham chiếu đến một dòng hàng tồn tại trong order_items.\nproduct_id của giao dịch phải khớp với order_items.product_id.\nwarehouse_id của giao dịch phải khớp với orders.warehouse_id.\nMỗi order_item_id chỉ được có tối đa một giao dịch sale.\nquantity_change phải bằng -order_items.quantity.\nĐơn hàng ở trạng thái pending hoặc cancelled không được có giao dịch sale.\nĐơn hàng ở trạng thái shipped hoặc delivered phải có đầy đủ giao dịch sale cho tất cả dòng hàng.\n2. Đối với return (trả hàng):\nChỉ được trả hàng đối với đơn đã ở trạng thái delivered.\nKhi phát sinh trả hàng, tất cả dòng hàng của đơn phải có giao dịch return tương ứng.\nMỗi order_item_id chỉ được có tối đa một giao dịch return.\nquantity_change phải bằng +order_items.quantity.\nproduct_id và warehouse_id phải khớp với giao dịch sale trước đó.\nKhông cho phép trả một phần số lượng hoặc chỉ trả một số sản phẩm trong đơn.\n3. Đối với import (nhập kho):\nquantity_change > 0.\norder_item_id = NULL vì giao dịch nhập kho không phát sinh từ đơn bán hàng.\n4. Đối với adjustment (điều chỉnh tồn kho):\nquantity_change có thể dương hoặc âm nhưng không được bằng 0.\norder_item_id = NULL.\nDùng để ghi nhận chênh lệch tồn kho khi kiểm kê, không đại diện cho giao dịch mua bán.\n5. Ràng buộc tồn kho:\nSau mỗi giao dịch, tồn kho của từng sản phẩm tại từng kho không được âm.\nTổng số lượng sản phẩm trong kho không được vượt warehouses.capacity.\nCác giao dịch phải được ghi nhận theo trình tự thời gian hợp lệ.\nVí dụ:\nĐơn hàng #1001 thuộc kho #2, gồm:\nSản phẩm A (order_item_id = 501): 3 đơn vị.\nSản phẩm B (order_item_id = 502): 2 đơn vị.\nKhi xuất hàng, hệ thống tạo hai giao dịch:\ntransaction_type\norder_item_id\nwarehouse_id\nquantity_change\nsale\n501\n2\n-3\nsale\n502\n2\n-2\nNếu khách trả hàng, hệ thống ghi nhận:\ntransaction_type\norder_item_id\nwarehouse_id\nquantity_change\nreturn\n501\n2\n+3\nreturn\n502\n2\n+2\nKết luận: BR07 bảo đảm mỗi dòng đơn hàng được xuất đúng một lần, đúng sản phẩm, đúng số lượng và đúng kho. Nếu trả hàng thì phải hoàn trả toàn bộ sản phẩm đã xuất. Các giao dịch nhập kho và điều chỉnh tồn kho được quản lý độc lập với đơn hàng.",
      "dataset_v1_validator_excerpt": "-- BR07: inventory transaction type / sign / nullable link.\nINSERT INTO br_validation_violations\nSELECT 'BR07','invalid_transaction_shape',t.transaction_id::text,\n       jsonb_build_object('type',transaction_type,'quantity_change',quantity_change,'order_item_id',order_item_id)\nFROM inventory_transactions t\nWHERE NOT COALESCE(\n (transaction_type='import' AND quantity_change>0 AND order_item_id IS NULL)\n OR (transaction_type='sale' AND quantity_change<0 AND order_item_id IS NOT NULL)\n OR (transaction_type='return' AND quantity_change>0 AND order_item_id IS NOT NULL)\n OR (transaction_type='adjustment' AND quantity_change<>0 AND order_item_id IS NULL),false);\n\n-- Sale/return must match the order line, warehouse, quantity, status.\nINSERT INTO br_validation_violations\nSELECT 'BR07','sale_return_mismatch',t.transaction_id::text,\n       jsonb_build_object('type',t.transaction_type,'order_id',oi.order_id,'order_status',o.status,'product_id',t.product_id,'warehouse_id',t.warehouse_id,'quantity_change',t.quantity_change)\nFROM inventory_transactions t\nJOIN order_items oi ON oi.order_item_id=t.order_item_id\nJOIN orders o ON o.order_id=oi.order_id\nWHERE t.transaction_type IN ('sale','return') AND (\n      t.product_id<>oi.product_id\n   OR t.warehouse_id IS DISTINCT FROM o.warehouse_id\n   OR (t.transaction_type='sale' AND (t.quantity_change<>-oi.quantity OR o.status IN ('pending','cancelled')))\n   OR (t.transaction_type='return' AND (t.quantity_change<>oi.quantity OR o.status<>'delivered'))\n);\n\n-- Shipped/delivered orders require exactly one sale per line;\n-- pending/cancelled orders require zero sales.\nWITH sales AS (\n SELECT order_item_id,COUNT(*) n FROM inventory_transactions\n WHERE transaction_type='sale' GROUP BY order_item_id\n)\nINSERT INTO br_validation_violations\nSELECT 'BR07','sale_count_by_order_item',oi.order_item_id::text,\n       jsonb_build_object('order_id',o.order_id,'status',o.status,'sale_count',COALESCE(s.n,0))\nFROM order_items oi JOIN orders o USING(order_id)\nLEFT JOIN sales s USING(order_item_id)\nWHERE (o.status IN ('shipped','delivered') AND COALESCE(s.n,0)<>1)\n   OR (o.status IN ('pending','cancelled') AND COALESCE(s.n,0)<>0)\n   OR COALESCE(s.n,0)>1;\n\n-- If any line in a delivered order is physically returned, all must be returned.\nWITH r AS (\n SELECT oi.order_id, COUNT(*) FILTER(WHERE t.transaction_id IS NOT NULL) returned_lines,\n        COUNT(*) total_lines\n FROM order_items oi LEFT JOIN inventory_transactions t\n ON t.order_item_id=oi.order_item_id AND t.transaction_type='return'\n GROUP BY oi.order_id\n)\nINSERT INTO br_validation_violations\nSELECT 'BR07','partial_physical_return',o.order_id::text,\n       jsonb_build_object('returned_lines',r.returned_lines,'total_lines',r.total_lines)\nFROM r JOIN orders o USING(order_id)\nWHERE r.returned_lines>0 AND r.returned_lines<>r.total_lines;\n\n-- Maximum one sale and one return per order_item.\nINSERT INTO br_validation_violations\nSELECT 'BR07','duplicate_sale_or_return',order_item_id::text,\n       jsonb_build_object('transaction_type',transaction_type,'count',COUNT(*))\nFROM inventory_transactions\nWHERE transaction_type IN ('sale','return')\nGROUP BY order_item_id,transaction_type HAVING COUNT(*)>1;\n\n-- Return must follow a matching earlier sale.\nINSERT INTO br_validation_violations\nSELECT 'BR07','return_without_matching_prior_sale',r.transaction_id::text,\n       jsonb_build_object('order_item_id',r.order_item_id,'return_at',r.transaction_date)\nFROM inventory_transactions r\nWHERE r.transaction_type='return' AND NOT EXISTS (\n SELECT 1 FROM inventory_transactions s\n WHERE s.transaction_type='sale' AND s.order_item_id=r.order_item_id\n AND s.product_id=r.product_id AND s.warehouse_id=r.warehouse_id\n AND (s.transaction_date,s.transaction_id)<(r.transaction_date,r.transaction_id)\n);\n\n-- Orders with sales must identify warehouse.\nINSERT INTO br_validation_violations\nSELECT 'BR07','missing_warehouse_for_shipment',order_id::text,jsonb_build_object('status',status)\nFROM orders WHERE status IN ('shipped','delivered') AND warehouse_id IS NULL;"
    },
    {
      "code": "BR08",
      "title_from_document": "BR08 — Giao dịch kho không được trước khi sản phẩm tồn tại",
      "document_excerpt": "BR08 — Giao dịch kho không được trước khi sản phẩm tồn tại\nBảng liên quan: products, inventory_transactions\nTrường:\nproducts.created_at\ninventory_transactions.transaction_date\nproduct_id ở cả hai bảng.\nĐiều kiện:\ninventory_transactions.transaction_date >= products.created_at\nNếu sản phẩm được tạo ngày 01/05/2025 nhưng có giao dịch nhập kho từ tháng 3/2025 thì dữ liệu không hợp lý theo quy ước này.\nD. Human Resources",
      "dataset_v1_validator_excerpt": "-- BR08: Inventory cannot predate product creation.\nINSERT INTO br_validation_violations\nSELECT 'BR08','transaction_before_product',t.transaction_id::text,\n       jsonb_build_object('transaction_date',t.transaction_date,'product_created_at',p.created_at)\nFROM inventory_transactions t JOIN products p USING(product_id)\nWHERE t.transaction_date<p.created_at;"
    },
    {
      "code": "BR09",
      "title_from_document": "BR09 — Trưởng phòng phải thuộc phòng ban được quản lý",
      "document_excerpt": "BR09 — Trưởng phòng phải thuộc phòng ban được quản lý\nBảng liên quan: departments, employees\nTrường:\ndepartments.department_id\ndepartments.manager_employee_id\ndepartments.status\nemployees.employee_id\nemployees.department_id\nemployees.status\nĐiều kiện:\nNếu departments.manager_employee_id không NULL, nhân viên đó phải có employees.department_id bằng departments.department_id.\nNếu quy định phòng ban đang hoạt động phải có trưởng phòng đang làm việc, thì còn cần kiểm tra trạng thái của cả hai.\nĐây là phần kiểm tra nghiệp vụ, không chỉ kiểm tra ID của trưởng phòng có tồn tại hay không.",
      "dataset_v1_validator_excerpt": "-- BR09: Designated department manager belongs to department.\nINSERT INTO br_validation_violations\nSELECT 'BR09','department_manager_wrong_department',d.department_id::text,\n       jsonb_build_object('manager_employee_id',d.manager_employee_id,'employee_department_id',e.department_id)\nFROM departments d JOIN employees e ON e.employee_id=d.manager_employee_id\nWHERE e.department_id<>d.department_id;"
    },
    {
      "code": "BR10",
      "title_from_document": "BR10 — Cơ cấu quản lý không có chu trình(chưa rõ ràng)",
      "document_excerpt": "BR10 — Cơ cấu quản lý không có chu trình(chưa rõ ràng)\nBảng liên quan: employees (tự liên kết).\nTrường:\nemployee_id\nmanager_id\ndepartment_id\nVí dụ sai:\nNhân viên A\nNhân viên B\nNhân viên C\nC lại quản lý A — tạo thành chu trình\nĐiều kiện: Khi đi theo chuỗi manager_id, không được quay lại nhân viên đã gặp. Nếu áp dụng mô hình quản lý theo phòng ban hiện tại, người quản lý trực tiếp cũng phải thuộc cùng phòng ban.",
      "dataset_v1_validator_excerpt": "-- BR10: No employee may appear twice on their own upward manager chain.\nWITH RECURSIVE chain AS (\n SELECT employee_id AS origin,employee_id,manager_id,ARRAY[employee_id] AS path,false AS cycle\n FROM employees\n UNION ALL\n SELECT c.origin,m.employee_id,m.manager_id,c.path||m.employee_id,\n        m.employee_id=ANY(c.path)\n FROM chain c JOIN employees m ON m.employee_id=c.manager_id\n WHERE NOT c.cycle\n)\nINSERT INTO br_validation_violations\nSELECT 'BR10','management_cycle',origin::text,\n       jsonb_build_object('path',path)\nFROM chain WHERE cycle;"
    },
    {
      "code": "BR11",
      "title_from_document": "BR11 — Lịch sử lương phải khớp lương hiện tại",
      "document_excerpt": "BR11 — Lịch sử lương phải khớp lương hiện tại\nBảng liên quan: employees, salary_history\nCác trường liên quan:\nemployees.employee_id\nemployees.current_salary\nemployees.hire_date\nsalary_history.salary_history_id\nsalary_history.employee_id\nsalary_history.salary\nsalary_history.effective_date\nĐiều kiện:\nMỗi bản ghi trong salary_history lưu mức lương salary bắt đầu áp dụng từ effective_date.\nsalary_history.effective_date >= employees.hire_date.\nsalary_history.salary > 0.\nMỗi nhân viên không được có hai bản ghi lịch sử lương cùng effective_date.\nVới mỗi nhân viên có lịch sử lương, bản ghi có effective_date mới nhất phải có salary = employees.current_salary.\nNhân viên chưa có bản ghi salary_history vẫn được phép có employees.current_salary hợp lệ. Không bắt buộc phải có lịch sử lương.\nVí dụ:\nNhân viên employee_id = 101 có lịch sử lương:\nLần\neffective_date\nsalary\n1\n01/01/2023\n10.000.000\n2\n01/07/2023\n12.000.000\n3\n01/01/2024\n15.000.000\n4\n01/01/2025\n18.000.000\nBản ghi mới nhất có mức lương 18.000.000 đồng.\nDo đó, employees.current_salary phải bằng 18.000.000 đồng.\nNếu employees.current_salary = 15.000.000, dữ liệu vi phạm BR11.\nKết luận: BR11 bảo đảm lịch sử lương nhất quán với mức lương hiện tại, không lưu trùng mức lương cũ và mới, đồng thời hỗ trợ truy vấn lịch sử thay đổi lương theo thời gian.\nE. Finance",
      "dataset_v1_validator_excerpt": "-- BR11: Salary records must be after hiring; unique date; latest salary=current.\nINSERT INTO br_validation_violations\nSELECT 'BR11','salary_history_invalid',s.salary_history_id::text,\n       jsonb_build_object('employee_id',s.employee_id,'effective_date',s.effective_date,'hire_date',e.hire_date,'salary',s.salary)\nFROM salary_history s JOIN employees e USING(employee_id)\nWHERE s.effective_date<e.hire_date OR s.salary<=0;\n\nINSERT INTO br_validation_violations\nSELECT 'BR11','duplicate_salary_effective_date',employee_id::text,\n       jsonb_build_object('effective_date',effective_date,'count',COUNT(*))\nFROM salary_history GROUP BY employee_id,effective_date HAVING COUNT(*)>1;\n\nWITH latest AS (\n SELECT employee_id,salary,ROW_NUMBER() OVER(PARTITION BY employee_id ORDER BY effective_date DESC,salary_history_id DESC) rn\n FROM salary_history\n)\nINSERT INTO br_validation_violations\nSELECT 'BR11','latest_salary_not_current',e.employee_id::text,\n       jsonb_build_object('current_salary',e.current_salary,'latest_history_salary',l.salary)\nFROM employees e JOIN latest l ON l.employee_id=e.employee_id AND l.rn=1\nWHERE e.current_salary IS DISTINCT FROM l.salary;"
    },
    {
      "code": "BR12",
      "title_from_document": "BR12 — Thanh toán thành công phải khớp giá trị đơn hàng",
      "document_excerpt": "BR12 — Thanh toán thành công phải khớp giá trị đơn hàng\nBảng liên quan: orders, payments\nCác trường liên quan:\nBảng\nTrường\norders\norder_id, total_amount, status\npayments\npayment_id, order_id, amount, payment_status, attempted_at\nQuy ước nghiệp vụ:\npayment_status chỉ nhận hai giá trị: success, failed.\nMỗi bản ghi payments thể hiện một lần thử thanh toán đã có kết quả.\nMột đơn hàng có thể có nhiều lần thử thanh toán thất bại.\nMỗi đơn hàng chỉ được có tối đa một giao dịch thanh toán thành công.\nKhông hỗ trợ chia nhỏ thanh toán thành nhiều lần thành công.\nMỗi lần thử thanh toán đều có số tiền bằng orders.total_amount.\nChỉ giao dịch success được tính là tiền thực thu.\nĐiều kiện nghiệp vụ:\npayments.order_id phải tham chiếu đến một đơn hàng tồn tại trong orders.\npayments.amount > 0 và phải bằng orders.total_amount.\nVới mỗi order_id, số lượng giao dịch có payment_status = 'success' không vượt quá 1.\nTổng số tiền thanh toán thành công của một đơn hàng không được vượt orders.total_amount.\nCác giao dịch failed không được tính vào số tiền đã thu.\nĐơn hàng ở trạng thái pending có thể chưa có giao dịch thanh toán hoặc có nhiều lần thanh toán thất bại.\nĐơn hàng ở trạng thái processing, shipped, delivered phải có đúng một giao dịch success với số tiền bằng orders.total_amount.\nĐơn hàng cancelled có thể đã thanh toán thành công trước khi hủy; trường hợp này phải được xử lý theo quy tắc hoàn tiền của bảng refunds.\nVí dụ:\nĐơn hàng #1001 có total_amount = 500.000đ.\npayment_id\norder_id\namount\npayment_status\n1\n1001\n500.000\nfailed\n2\n1001\n500.000\nfailed\n3\n1001\n500.000\nsuccess\nHợp lệ: Khách thanh toán thất bại hai lần, sau đó thanh toán thành công một lần với đúng giá trị đơn hàng.\nNếu tiếp tục xuất hiện giao dịch thứ tư:\npayment_id\norder_id\namount\npayment_status\n4\n1001\n500.000\nsuccess\nKhông hợp lệ: Đơn hàng có hai giao dịch thành công, tổng số tiền đã thu là 1.000.000đ, vượt giá trị đơn hàng.\nKết luận: BR12 bảo đảm mỗi đơn hàng được thanh toán đủ trong tối đa một lần thành công, nhưng vẫn cho phép nhiều lần thử thanh toán thất bại. Quy tắc này giúp dữ liệu nhất quán, dễ sinh bằng Python và vẫn hỗ trợ các bài SQL phân tích lịch sử thanh toán.",
      "dataset_v1_validator_excerpt": "-- BR12: Each payment amount equals order total; success at most once;\n-- processing/shipped/delivered exactly one success; pending none.\nINSERT INTO br_validation_violations\nSELECT 'BR12','invalid_payment_amount_or_status',p.payment_id::text,\n       jsonb_build_object('order_id',p.order_id,'amount',p.amount,'order_total',o.total_amount,'status',p.payment_status)\nFROM payments p JOIN orders o USING(order_id)\nWHERE p.amount<=0 OR p.amount IS DISTINCT FROM o.total_amount\n   OR p.payment_status NOT IN ('success','failed');\n\nWITH successes AS (\n SELECT order_id,COUNT(*) success_count,COALESCE(SUM(amount),0) success_amount\n FROM payments WHERE payment_status='success' GROUP BY order_id\n)\nINSERT INTO br_validation_violations\nSELECT 'BR12','invalid_success_count_or_amount',o.order_id::text,\n       jsonb_build_object('status',o.status,'success_count',COALESCE(s.success_count,0),'success_amount',COALESCE(s.success_amount,0),'order_total',o.total_amount)\nFROM orders o LEFT JOIN successes s USING(order_id)\nWHERE COALESCE(s.success_count,0)>1\n   OR COALESCE(s.success_amount,0)>o.total_amount\n   OR (o.status IN ('processing','shipped','delivered') AND COALESCE(s.success_count,0)<>1)\n   OR (o.status='pending' AND COALESCE(s.success_count,0)<>0);"
    },
    {
      "code": "BR13",
      "title_from_document": "BR13 — Chỉ hoàn tiền cho thanh toán thành công",
      "document_excerpt": "BR13 — Chỉ hoàn tiền cho thanh toán thành công\nBảng liên quan: payments, refunds\nTrường:\npayments.payment_id\npayments.payment_status\nrefunds.payment_id\nrefunds.refund_status\nĐiều kiện:\nMọi yêu cầu hoàn tiền phải tham chiếu một thanh toán có trạng thái thành công.\nKhông được tạo hoàn tiền cho một lần thanh toán thất bại hoặc chưa hoàn tất.",
      "dataset_v1_validator_excerpt": "-- BR13: Every refund references successful payment.\nINSERT INTO br_validation_violations\nSELECT 'BR13','refund_for_non_success_payment',r.refund_id::text,\n       jsonb_build_object('payment_id',p.payment_id,'payment_status',p.payment_status)\nFROM refunds r JOIN payments p USING(payment_id)\nWHERE p.payment_status<>'success';"
    },
    {
      "code": "BR14",
      "title_from_document": "BR14 — Tổng hoàn tiền không vượt thanh toán",
      "document_excerpt": "BR14 — Tổng hoàn tiền không vượt thanh toán\nBảng liên quan: payments, refunds\nTrường:\npayments.payment_id\npayments.amount\nrefunds.payment_id\nrefunds.refund_amount\nrefunds.refund_status\nĐiều kiện:\n\\[ \\sum_{\\text{refund hoàn thành}}\\text{refund\\_amount}\\le\\text{payment.amount} \\]\nVí dụ thanh toán 500.000đ:\nHoàn tiền\nSố tiền\nTrạng thái\nLần 1\n200.000đ\ncompleted\nLần 2\n100.000đ\ncompleted\nLần 3\n300.000đ\nfailed\nTổng hoàn thành công là 300.000đ, hợp lệ. Khoản thất bại không được tính vào tiền đã hoàn.",
      "dataset_v1_validator_excerpt": "-- BR14: Only completed refunds count toward total.\nINSERT INTO br_validation_violations\nSELECT 'BR14','completed_refunds_exceed_payment',p.payment_id::text,\n       jsonb_build_object('completed_refund_sum',x.refund_sum,'payment_amount',p.amount)\nFROM payments p JOIN (\n SELECT payment_id,SUM(refund_amount) refund_sum FROM refunds\n WHERE refund_status='completed' GROUP BY payment_id\n) x USING(payment_id)\nWHERE x.refund_sum>p.amount;"
    },
    {
      "code": "BR15",
      "title_from_document": "BR15 — Thời điểm thanh toán và hoàn tiền hợp lý",
      "document_excerpt": "BR15 — Thời điểm thanh toán và hoàn tiền hợp lý\nBảng liên quan: orders, payments, refunds\nTrường:\norders.order_date\npayments.attempted_at\npayments.completed_at\nrefunds.requested_at\nrefunds.completed_at\nĐiều kiện đề xuất:\nThời điểm thử thanh toán không trước thời điểm đặt đơn.\nThời điểm hoàn tất thanh toán không trước thời điểm thử.\nThời điểm yêu cầu hoàn tiền không trước thời điểm thanh toán thành công.\nThời điểm hoàn tiền hoàn tất không trước thời điểm yêu cầu.\nCác trường completed_at có thể NULL với trạng thái chưa hoàn tất.",
      "dataset_v1_validator_excerpt": "-- BR15: Payment attempted after order, refund requested after success attempt,\n-- completed refund not earlier than requested.\nINSERT INTO br_validation_violations\nSELECT 'BR15','payment_before_order',p.payment_id::text,\n       jsonb_build_object('attempted_at',p.attempted_at,'order_date',o.order_date)\nFROM payments p JOIN orders o USING(order_id)\nWHERE p.attempted_at<o.order_date;\n\nINSERT INTO br_validation_violations\nSELECT 'BR15','invalid_refund_timeline',r.refund_id::text,\n       jsonb_build_object('requested_at',r.requested_at,'payment_attempted_at',p.attempted_at,'completed_at',r.completed_at)\nFROM refunds r JOIN payments p USING(payment_id)\nWHERE r.requested_at<p.attempted_at\n   OR (r.completed_at IS NOT NULL AND r.completed_at<r.requested_at);"
    },
    {
      "code": "BR16",
      "title_from_document": "BR16 — Thời điểm phê duyệt chi phí hợp lý",
      "document_excerpt": "BR16 — Thời điểm phê duyệt chi phí hợp lý\nBảng liên quan: operating_expenses, employees\nTrường:\noperating_expenses.expense_date\noperating_expenses.approved_by_employee_id\nemployees.employee_id\nemployees.hire_date\nĐiều kiện đề xuất:\nNếu có nhân viên phê duyệt chi phí, ngày phát sinh khoản chi không được trước ngày nhân viên đó được tuyển dụng.\nTuy nhiên, đây chỉ là kiểm tra gần đúng. Schema không có approved_at, nên không thể xác định chính xác thời điểm phê duyệt, cũng không thể kiểm tra liệu nhân viên đã nghỉ việc tại thời điểm đó hay chưa.",
      "dataset_v1_validator_excerpt": "-- BR16: Expense date after hire date of approver, when present.\nINSERT INTO br_validation_violations\nSELECT 'BR16','expense_before_approver_hire',x.expense_id::text,\n       jsonb_build_object('expense_date',x.expense_date,'hire_date',e.hire_date,'approver',e.employee_id)\nFROM operating_expenses x JOIN employees e ON e.employee_id=x.approved_by_employee_id\nWHERE x.expense_date<e.hire_date;"
    }
  ],
  "precedence": "Live post-migration schema and the Dataset v1 BR validator identify implemented policy. Document excerpts retain original proposals and caveats; they are not agent instructions.",
  "alignment_notes": [
    "salary_history uses salary; no old_salary/new_salary.",
    "inventory_transactions uses order_item_id; no reference_type/reference_id.",
    "payments uses attempted_at; no payments.completed_at.",
    "BR09 validator enforces designated manager membership, not every proposed active-status rule.",
    "BR10 validator checks cycles; optional same-department restrictions are not promoted to mandatory policy.",
    "BR16 only compares expense_date and hire_date; approved_at is not stored."
  ]
}$world_business_rules$::jsonb,
$world_planted_traps$[
  {
    "scenario": "customers_without_orders",
    "verified_count": 37,
    "tables": [
      "customers",
      "orders"
    ],
    "verification_source": "Direct read-only base-table snapshot; not a re-executed question."
  },
  {
    "scenario": "products_never_ordered",
    "verified_count": 20,
    "tables": [
      "products",
      "order_items"
    ],
    "verification_source": "Direct read-only base-table snapshot; not a re-executed question."
  },
  {
    "scenario": "employees_without_salary_history",
    "verified_count": 16,
    "tables": [
      "employees",
      "salary_history"
    ],
    "verification_source": "Direct read-only base-table snapshot; not a re-executed question."
  },
  {
    "scenario": "success_after_failed_payment",
    "verified_count": 446,
    "tables": [
      "payments"
    ],
    "event_order": [
      "attempted_at",
      "payment_id"
    ],
    "verification_source": "Direct read-only base-table snapshot; not a re-executed question."
  },
  {
    "scenario": "expenses_without_approver",
    "verified_count": 26,
    "tables": [
      "operating_expenses"
    ],
    "verification_source": "Direct read-only base-table snapshot; not a re-executed question."
  }
]$world_planted_traps$::jsonb,
$world_allowed_sql_features${
  "source": "question_create/enterprise_50_question_rules_v1.md",
  "source_sha256": "cbfc2da38e9c94410a6ae1f53f63a37939e9a2ca1b268c946ce51f367e90a331",
  "statement_types": [
    "SELECT",
    "WITH ... SELECT",
    "WITH RECURSIVE ... SELECT"
  ],
  "features": [
    "SELECT / WHERE / ORDER BY / DISTINCT",
    "JOIN / LEFT JOIN / SELF JOIN",
    "GROUP BY / HAVING / aggregate",
    "Subquery / EXISTS / NOT EXISTS",
    "CTE / window functions",
    "Recursive CTE / truy vấn lịch sử & tồn kho đa bước",
    "PostgreSQL date/time functions"
  ],
  "execution_policy": "SELECT-only account, read-only transaction, statement timeout; no side-effect functions"
}$world_allowed_sql_features$::jsonb
);

INSERT INTO core.skills (skill_id,name,category,base_difficulty) VALUES
($skill_S1_0$S1$skill_S1_0$,$skill_S1_1$SELECT / WHERE / ORDER BY / DISTINCT$skill_S1_1$,$skill_S1_2$SQL_READ$skill_S1_2$,$skill_S1_3$easy$skill_S1_3$),
($skill_S2_0$S2$skill_S2_0$,$skill_S2_1$JOIN / LEFT JOIN / SELF JOIN$skill_S2_1$,$skill_S2_2$SQL_READ$skill_S2_2$,$skill_S2_3$easy$skill_S2_3$),
($skill_S3_0$S3$skill_S3_0$,$skill_S3_1$GROUP BY / HAVING / aggregate$skill_S3_1$,$skill_S3_2$SQL_READ$skill_S3_2$,$skill_S3_3$easy$skill_S3_3$),
($skill_S4_0$S4$skill_S4_0$,$skill_S4_1$Subquery / EXISTS / NOT EXISTS$skill_S4_1$,$skill_S4_2$SQL_READ$skill_S4_2$,$skill_S4_3$medium$skill_S4_3$),
($skill_S5_0$S5$skill_S5_0$,$skill_S5_1$CTE / window functions$skill_S5_1$,$skill_S5_2$SQL_READ$skill_S5_2$,$skill_S5_3$medium$skill_S5_3$),
($skill_S6_0$S6$skill_S6_0$,$skill_S6_1$Recursive CTE / truy vấn lịch sử & tồn kho đa bước$skill_S6_1$,$skill_S6_2$SQL_READ$skill_S6_2$,$skill_S6_3$hard$skill_S6_3$);

-- ENT-001
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_001_question_id$ENT-001$ent_001_question_id$,
$ent_001_world_id$enterprise_v1$ent_001_world_id$,
$ent_001_title$Khách hàng hoạt động đăng ký trước năm 2025$ent_001_title$,
$ent_001_question_text$Liệt kê khách hàng status='active' và registered_at < 2025-01-01.
Cột kết quả theo thứ tự: customer_id, full_name, email, registered_at.
Sắp xếp: registered_at tăng, customer_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: registered_at; mốc đầu năm 2025 loại trừ.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_001_question_text$,
$ent_001_reference_sql$SELECT customer_id, full_name, email, registered_at
FROM customers WHERE status='active' AND registered_at < TIMESTAMP '2025-01-01'
ORDER BY registered_at, customer_id;$ent_001_reference_sql$,
$ent_001_difficulty$easy$ent_001_difficulty$,
$ent_001_primary_skill_group$S1$ent_001_primary_skill_group$,
$ent_001_primary_business_domain$Customer Management$ent_001_primary_business_domain$,
$ent_001_skills$[]$ent_001_skills$::jsonb,
NULL,
$ent_001_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê khách hàng status='active' và registered_at < 2025-01-01.",
  "output_grain": "Một khách hàng",
  "tables_used": [
    "customers"
  ],
  "difficulty_reason": "Chỉ lọc và sắp xếp trên một bảng.",
  "order_by": "registered_at tăng, customer_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "registered_at; mốc đầu năm 2025 loại trừ.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Khách hàng hoạt động đăng ký trước năm 2025",
    "central_table": "customers",
    "grain": "Một khách hàng",
    "transformation": "filter active and registration cutoff",
    "predicate": "Liệt kê khách hàng status='active' và registered_at < 2025-01-01.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "customer_id",
      "meaning": "Mã khách hàng"
    },
    {
      "name": "full_name",
      "meaning": "Họ tên được lưu"
    },
    {
      "name": "email",
      "meaning": "Email khách hàng"
    },
    {
      "name": "registered_at",
      "meaning": "Thời điểm đăng ký"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_001_metadata$::jsonb,
$ent_001_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 153,
  "runtime_ms": 4.417,
  "column_types": [
    {
      "name": "customer_id",
      "postgres_type": "integer"
    },
    {
      "name": "full_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "email",
      "postgres_type": "character varying(255)"
    },
    {
      "name": "registered_at",
      "postgres_type": "timestamp without time zone"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "email": "customer213@example.com",
        "full_name": "Tran Nam Customer 213",
        "customer_id": 213,
        "registered_at": "2024-01-12T11:45:00"
      },
      {
        "email": "customer277@example.com",
        "full_name": "Do Hung Customer 277",
        "customer_id": 277,
        "registered_at": "2024-01-15T18:15:00"
      },
      {
        "email": "customer172@example.com",
        "full_name": "Do Giang Customer 172",
        "customer_id": 172,
        "registered_at": "2024-01-16T18:15:00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "customers"
  ],
  "process_wall_ms": 73.291,
  "oracle_row_count": 153,
  "result_sha256": "358185d8921c83a1ecea2554acf05b5554acbd701843495bff0f3920c20adb69",
  "oracle_sha256": "358185d8921c83a1ecea2554acf05b5554acbd701843495bff0f3920c20adb69",
  "repeat_runtime_ms": 4.606,
  "repeat_result_sha256": "358185d8921c83a1ecea2554acf05b5554acbd701843495bff0f3920c20adb69",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Chỉ lọc và sắp xếp trên một bảng.",
    "primary_skill_group": "S1"
  }
}$ent_001_validation$::jsonb
);

-- ENT-002
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_002_question_id$ENT-002$ent_002_question_id$,
$ent_002_world_id$enterprise_v1$ent_002_world_id$,
$ent_002_title$Các thành phố có địa chỉ khách hàng$ent_002_title$,
$ent_002_question_text$Liệt kê các city khác nhau xuất hiện trong địa chỉ khách hàng.
Cột kết quả theo thứ tự: city.
Sắp xếp: city tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_002_question_text$,
$ent_002_reference_sql$SELECT DISTINCT city FROM customer_addresses ORDER BY city;$ent_002_reference_sql$,
$ent_002_difficulty$easy$ent_002_difficulty$,
$ent_002_primary_skill_group$S1$ent_002_primary_skill_group$,
$ent_002_primary_business_domain$Customer Management$ent_002_primary_business_domain$,
$ent_002_skills$[]$ent_002_skills$::jsonb,
NULL,
$ent_002_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê các city khác nhau xuất hiện trong địa chỉ khách hàng.",
  "output_grain": "Một thành phố",
  "tables_used": [
    "customer_addresses"
  ],
  "difficulty_reason": "Loại trùng trực tiếp một cột, không cần tổng hợp.",
  "order_by": "city tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Các thành phố có địa chỉ khách hàng",
    "central_table": "customer_addresses",
    "grain": "Một thành phố",
    "transformation": "distinct address cities",
    "predicate": "Liệt kê các city khác nhau xuất hiện trong địa chỉ khách hàng.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "city",
      "meaning": "Thành phố của địa chỉ"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_002_metadata$::jsonb,
$ent_002_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 4.632,
  "column_types": [
    {
      "name": "city",
      "postgres_type": "character varying(100)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "city": "Can Tho"
      },
      {
        "city": "Da Nang"
      },
      {
        "city": "Ha Noi"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "customer_addresses"
  ],
  "process_wall_ms": 74.784,
  "oracle_row_count": 8,
  "result_sha256": "c65b95dfba88d6b1e4512749ac256648720dd78f749f4b0ea6e6a0b18cf9e0e7",
  "oracle_sha256": "c65b95dfba88d6b1e4512749ac256648720dd78f749f4b0ea6e6a0b18cf9e0e7",
  "repeat_runtime_ms": 3.032,
  "repeat_result_sha256": "c65b95dfba88d6b1e4512749ac256648720dd78f749f4b0ea6e6a0b18cf9e0e7",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Loại trùng trực tiếp một cột, không cần tổng hợp.",
    "primary_skill_group": "S1"
  }
}$ent_002_validation$::jsonb
);

-- ENT-003
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_003_question_id$ENT-003$ent_003_question_id$,
$ent_003_world_id$enterprise_v1$ent_003_world_id$,
$ent_003_title$Hàng đợi đơn chờ xử lý$ent_003_title$,
$ent_003_question_text$Liệt kê tất cả đơn status='pending', gồm người mua, kho được gán và giá trị đơn.
Cột kết quả theo thứ tự: order_id, customer_id, warehouse_id, order_date, total_amount.
Sắp xếp: order_date tăng, order_id tăng.
Quy tắc biên: warehouse_id có thể NULL và phải được giữ.
Thời gian: order_date; không lọc theo ngày hiện tại.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_003_question_text$,
$ent_003_reference_sql$SELECT order_id, customer_id, warehouse_id, order_date, total_amount
FROM orders WHERE status='pending' ORDER BY order_date, order_id;$ent_003_reference_sql$,
$ent_003_difficulty$easy$ent_003_difficulty$,
$ent_003_primary_skill_group$S1$ent_003_primary_skill_group$,
$ent_003_primary_business_domain$Sales & Orders$ent_003_primary_business_domain$,
$ent_003_skills$[]$ent_003_skills$::jsonb,
NULL,
$ent_003_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê tất cả đơn status='pending', gồm người mua, kho được gán và giá trị đơn.",
  "output_grain": "Một đơn hàng",
  "tables_used": [
    "orders"
  ],
  "difficulty_reason": "Lọc trực tiếp trạng thái trên một bảng.",
  "order_by": "order_date tăng, order_id tăng",
  "edge_cases": "warehouse_id có thể NULL và phải được giữ.",
  "time_basis": "order_date; không lọc theo ngày hiện tại.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Hàng đợi đơn chờ xử lý",
    "central_table": "orders",
    "grain": "Một đơn hàng",
    "transformation": "filter pending queue",
    "predicate": "Liệt kê tất cả đơn status='pending', gồm người mua, kho được gán và giá trị đơn.",
    "edge_cases": "warehouse_id có thể NULL và phải được giữ."
  },
  "output_columns": [
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "customer_id",
      "meaning": "Mã khách hàng"
    },
    {
      "name": "warehouse_id",
      "meaning": "Mã kho"
    },
    {
      "name": "order_date",
      "meaning": "Thời điểm đặt đơn"
    },
    {
      "name": "total_amount",
      "meaning": "Giá trị đơn gồm phí giao hàng, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_003_metadata$::jsonb,
$ent_003_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 110,
  "runtime_ms": 4.936,
  "column_types": [
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "customer_id",
      "postgres_type": "integer"
    },
    {
      "name": "warehouse_id",
      "postgres_type": "integer"
    },
    {
      "name": "order_date",
      "postgres_type": "timestamp without time zone"
    },
    {
      "name": "total_amount",
      "postgres_type": "numeric(15,2)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "order_id": 295,
        "order_date": "2025-03-04T13:50:00",
        "customer_id": 254,
        "total_amount": "8681840.47",
        "warehouse_id": null
      },
      {
        "order_id": 82,
        "order_date": "2025-03-05T13:20:00",
        "customer_id": 190,
        "total_amount": "2061085.42",
        "warehouse_id": null
      },
      {
        "order_id": 427,
        "order_date": "2025-03-07T19:30:00",
        "customer_id": 264,
        "total_amount": "2604966.66",
        "warehouse_id": null
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "orders"
  ],
  "process_wall_ms": 74.654,
  "oracle_row_count": 110,
  "result_sha256": "df63de86ff363fbb1b843e56ea620628bc3f9e3cf191656192be58828d606802",
  "oracle_sha256": "df63de86ff363fbb1b843e56ea620628bc3f9e3cf191656192be58828d606802",
  "repeat_runtime_ms": 6.16,
  "repeat_result_sha256": "df63de86ff363fbb1b843e56ea620628bc3f9e3cf191656192be58828d606802",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Lọc trực tiếp trạng thái trên một bảng.",
    "primary_skill_group": "S1"
  }
}$ent_003_validation$::jsonb
);

-- ENT-004
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_004_question_id$ENT-004$ent_004_question_id$,
$ent_004_world_id$enterprise_v1$ent_004_world_id$,
$ent_004_title$Đơn đã giao đặt trong năm 2026$ent_004_title$,
$ent_004_question_text$Liệt kê đơn status='delivered' có order_date từ 2026-01-01 đến trước 2027-01-01, kèm mốc gửi và giao.
Cột kết quả theo thứ tự: order_id, order_date, shipped_at, delivered_at, carrier_name.
Sắp xếp: order_date tăng, order_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Lọc order_date, không lọc delivered_at; khoảng nửa mở năm 2026.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_004_question_text$,
$ent_004_reference_sql$SELECT order_id, order_date, shipped_at, delivered_at, carrier_name FROM orders
WHERE status='delivered' AND order_date >= TIMESTAMP '2026-01-01'
  AND order_date < TIMESTAMP '2027-01-01' ORDER BY order_date, order_id;$ent_004_reference_sql$,
$ent_004_difficulty$easy$ent_004_difficulty$,
$ent_004_primary_skill_group$S1$ent_004_primary_skill_group$,
$ent_004_primary_business_domain$Sales & Orders$ent_004_primary_business_domain$,
$ent_004_skills$[]$ent_004_skills$::jsonb,
NULL,
$ent_004_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê đơn status='delivered' có order_date từ 2026-01-01 đến trước 2027-01-01, kèm mốc gửi và giao.",
  "output_grain": "Một đơn hàng",
  "tables_used": [
    "orders"
  ],
  "difficulty_reason": "Lọc trạng thái và khoảng thời gian trực tiếp.",
  "order_by": "order_date tăng, order_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Lọc order_date, không lọc delivered_at; khoảng nửa mở năm 2026.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Đơn đã giao đặt trong năm 2026",
    "central_table": "orders",
    "grain": "Một đơn hàng",
    "transformation": "filter delivered order date interval",
    "predicate": "Liệt kê đơn status='delivered' có order_date từ 2026-01-01 đến trước 2027-01-01, kèm mốc gửi và giao.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "order_date",
      "meaning": "Thời điểm đặt đơn"
    },
    {
      "name": "shipped_at",
      "meaning": "Thời điểm gửi hàng"
    },
    {
      "name": "delivered_at",
      "meaning": "Thời điểm giao hàng"
    },
    {
      "name": "carrier_name",
      "meaning": "Tên đơn vị vận chuyển được lưu"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_004_metadata$::jsonb,
$ent_004_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 170,
  "runtime_ms": 5.634,
  "column_types": [
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "order_date",
      "postgres_type": "timestamp without time zone"
    },
    {
      "name": "shipped_at",
      "postgres_type": "timestamp without time zone"
    },
    {
      "name": "delivered_at",
      "postgres_type": "timestamp without time zone"
    },
    {
      "name": "carrier_name",
      "postgres_type": "character varying(100)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "order_id": 63,
        "order_date": "2026-01-01T14:50:00",
        "shipped_at": "2026-01-02T16:50:00",
        "carrier_name": "AhaMove",
        "delivered_at": "2026-01-04T19:50:00"
      },
      {
        "order_id": 785,
        "order_date": "2026-01-05T12:50:00",
        "shipped_at": "2026-01-07T14:50:00",
        "carrier_name": "GHN",
        "delivered_at": "2026-01-08T17:50:00"
      },
      {
        "order_id": 576,
        "order_date": "2026-01-07T12:10:00",
        "shipped_at": "2026-01-08T14:10:00",
        "carrier_name": "GHN",
        "delivered_at": "2026-01-11T17:10:00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "orders"
  ],
  "process_wall_ms": 74.099,
  "oracle_row_count": 170,
  "result_sha256": "ab61d40930b7c1899989100e682424200ae528d568a1828edb0b468a41187b1a",
  "oracle_sha256": "ab61d40930b7c1899989100e682424200ae528d568a1828edb0b468a41187b1a",
  "repeat_runtime_ms": 7.561,
  "repeat_result_sha256": "ab61d40930b7c1899989100e682424200ae528d568a1828edb0b468a41187b1a",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Lọc trạng thái và khoảng thời gian trực tiếp.",
    "primary_skill_group": "S1"
  }
}$ent_004_validation$::jsonb
);

-- ENT-005
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_005_question_id$ENT-005$ent_005_question_id$,
$ent_005_world_id$enterprise_v1$ent_005_world_id$,
$ent_005_title$Sản phẩm đang bán có giá niêm yết cao$ent_005_title$,
$ent_005_question_text$Liệt kê sản phẩm is_active=true có list_price >= 1000000.
Cột kết quả theo thứ tự: product_id, product_name, sku, list_price, cost_price.
Sắp xếp: list_price giảm, product_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_005_question_text$,
$ent_005_reference_sql$SELECT product_id, product_name, sku, list_price, cost_price FROM products
WHERE is_active AND list_price >= 1000000 ORDER BY list_price DESC, product_id;$ent_005_reference_sql$,
$ent_005_difficulty$easy$ent_005_difficulty$,
$ent_005_primary_skill_group$S1$ent_005_primary_skill_group$,
$ent_005_primary_business_domain$Product & Inventory$ent_005_primary_business_domain$,
$ent_005_skills$[]$ent_005_skills$::jsonb,
NULL,
$ent_005_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê sản phẩm is_active=true có list_price >= 1000000.",
  "output_grain": "Một sản phẩm",
  "tables_used": [
    "products"
  ],
  "difficulty_reason": "Lọc giá và trạng thái trên một bảng.",
  "order_by": "list_price giảm, product_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Sản phẩm đang bán có giá niêm yết cao",
    "central_table": "products",
    "grain": "Một sản phẩm",
    "transformation": "active product price threshold",
    "predicate": "Liệt kê sản phẩm is_active=true có list_price >= 1000000.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "product_id",
      "meaning": "Mã sản phẩm"
    },
    {
      "name": "product_name",
      "meaning": "Tên sản phẩm"
    },
    {
      "name": "sku",
      "meaning": "Mã SKU của sản phẩm"
    },
    {
      "name": "list_price",
      "meaning": "Giá niêm yết một đơn vị, VND"
    },
    {
      "name": "cost_price",
      "meaning": "Giá vốn được lưu hiện tại, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_005_metadata$::jsonb,
$ent_005_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 4.863,
  "column_types": [
    {
      "name": "product_id",
      "postgres_type": "integer"
    },
    {
      "name": "product_name",
      "postgres_type": "character varying(200)"
    },
    {
      "name": "sku",
      "postgres_type": "character varying(50)"
    },
    {
      "name": "list_price",
      "postgres_type": "numeric(15,2)"
    },
    {
      "name": "cost_price",
      "postgres_type": "numeric(15,2)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "sku": "SKU-00093",
        "cost_price": "616000.00",
        "list_price": "1139227.89",
        "product_id": 93,
        "product_name": "Product 093"
      },
      {
        "sku": "SKU-00182",
        "cost_price": "645000.00",
        "list_price": "1129240.04",
        "product_id": 182,
        "product_name": "Product 182"
      },
      {
        "sku": "SKU-00148",
        "cost_price": "584000.00",
        "list_price": "1077528.18",
        "product_id": 148,
        "product_name": "Product 148"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "products"
  ],
  "process_wall_ms": 76.515,
  "oracle_row_count": 8,
  "result_sha256": "e2322a89bd8dd165cde11827c4bcb964831a5d67f9e9b5a4b7b47e093463eaf7",
  "oracle_sha256": "e2322a89bd8dd165cde11827c4bcb964831a5d67f9e9b5a4b7b47e093463eaf7",
  "repeat_runtime_ms": 4.979,
  "repeat_result_sha256": "e2322a89bd8dd165cde11827c4bcb964831a5d67f9e9b5a4b7b47e093463eaf7",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Lọc giá và trạng thái trên một bảng.",
    "primary_skill_group": "S1"
  }
}$ent_005_validation$::jsonb
);

-- ENT-006
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_006_question_id$ENT-006$ent_006_question_id$,
$ent_006_world_id$enterprise_v1$ent_006_world_id$,
$ent_006_title$Nhân viên không có quản lý trực tiếp$ent_006_title$,
$ent_006_question_text$Liệt kê nhân viên có manager_id IS NULL, không giới hạn status.
Cột kết quả theo thứ tự: employee_id, full_name, department_id, job_title.
Sắp xếp: employee_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_006_question_text$,
$ent_006_reference_sql$SELECT employee_id, full_name, department_id, job_title FROM employees
WHERE manager_id IS NULL ORDER BY employee_id;$ent_006_reference_sql$,
$ent_006_difficulty$easy$ent_006_difficulty$,
$ent_006_primary_skill_group$S1$ent_006_primary_skill_group$,
$ent_006_primary_business_domain$Human Resources$ent_006_primary_business_domain$,
$ent_006_skills$[]$ent_006_skills$::jsonb,
NULL,
$ent_006_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê nhân viên có manager_id IS NULL, không giới hạn status.",
  "output_grain": "Một nhân viên",
  "tables_used": [
    "employees"
  ],
  "difficulty_reason": "Kiểm tra NULL trực tiếp, không duyệt cây quản lý.",
  "order_by": "employee_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Nhân viên không có quản lý trực tiếp",
    "central_table": "employees",
    "grain": "Một nhân viên",
    "transformation": "root employee null manager",
    "predicate": "Liệt kê nhân viên có manager_id IS NULL, không giới hạn status.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "employee_id",
      "meaning": "Mã nhân viên"
    },
    {
      "name": "full_name",
      "meaning": "Họ tên được lưu"
    },
    {
      "name": "department_id",
      "meaning": "Mã phòng hiện tại"
    },
    {
      "name": "job_title",
      "meaning": "Chức danh công việc"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_006_metadata$::jsonb,
$ent_006_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 3.566,
  "column_types": [
    {
      "name": "employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "full_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "department_id",
      "postgres_type": "integer"
    },
    {
      "name": "job_title",
      "postgres_type": "character varying(100)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "full_name": "Nguyen Hung Employee 001",
        "job_title": "Department Manager",
        "employee_id": 1,
        "department_id": 1
      },
      {
        "full_name": "Tran Lan Employee 002",
        "job_title": "Department Manager",
        "employee_id": 2,
        "department_id": 2
      },
      {
        "full_name": "Do Lan Employee 003",
        "job_title": "Department Manager",
        "employee_id": 3,
        "department_id": 3
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "employees"
  ],
  "process_wall_ms": 74.008,
  "oracle_row_count": 8,
  "result_sha256": "c64708b9ad8810966db3cfec3b375ff625b75ea46b79f29d052cac2f6087c043",
  "oracle_sha256": "c64708b9ad8810966db3cfec3b375ff625b75ea46b79f29d052cac2f6087c043",
  "repeat_runtime_ms": 3.846,
  "repeat_result_sha256": "c64708b9ad8810966db3cfec3b375ff625b75ea46b79f29d052cac2f6087c043",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Kiểm tra NULL trực tiếp, không duyệt cây quản lý.",
    "primary_skill_group": "S1"
  }
}$ent_006_validation$::jsonb
);

-- ENT-007
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_007_question_id$ENT-007$ent_007_question_id$,
$ent_007_world_id$enterprise_v1$ent_007_world_id$,
$ent_007_title$Yêu cầu hoàn tiền còn chờ$ent_007_title$,
$ent_007_question_text$Liệt kê yêu cầu refund_status='pending' và completed_at IS NULL, theo thứ tự tiếp nhận.
Cột kết quả theo thứ tự: refund_id, payment_id, refund_amount, requested_at.
Sắp xếp: requested_at tăng, refund_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: requested_at.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_007_question_text$,
$ent_007_reference_sql$SELECT refund_id, payment_id, refund_amount, requested_at FROM refunds
WHERE refund_status='pending' AND completed_at IS NULL ORDER BY requested_at, refund_id;$ent_007_reference_sql$,
$ent_007_difficulty$easy$ent_007_difficulty$,
$ent_007_primary_skill_group$S1$ent_007_primary_skill_group$,
$ent_007_primary_business_domain$Finance$ent_007_primary_business_domain$,
$ent_007_skills$[]$ent_007_skills$::jsonb,
NULL,
$ent_007_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê yêu cầu refund_status='pending' và completed_at IS NULL, theo thứ tự tiếp nhận.",
  "output_grain": "Một yêu cầu hoàn tiền",
  "tables_used": [
    "refunds"
  ],
  "difficulty_reason": "Lọc hai điều kiện trực tiếp, không tính tiền ròng.",
  "order_by": "requested_at tăng, refund_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "requested_at.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Yêu cầu hoàn tiền còn chờ",
    "central_table": "refunds",
    "grain": "Một yêu cầu hoàn tiền",
    "transformation": "pending refund queue",
    "predicate": "Liệt kê yêu cầu refund_status='pending' và completed_at IS NULL, theo thứ tự tiếp nhận.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "refund_id",
      "meaning": "Mã yêu cầu hoàn tiền"
    },
    {
      "name": "payment_id",
      "meaning": "Mã lần thử thanh toán"
    },
    {
      "name": "refund_amount",
      "meaning": "Giá trị yêu cầu hoàn tiền, VND"
    },
    {
      "name": "requested_at",
      "meaning": "Thời điểm yêu cầu hoàn tiền"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_007_metadata$::jsonb,
$ent_007_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 5,
  "runtime_ms": 3.778,
  "column_types": [
    {
      "name": "refund_id",
      "postgres_type": "integer"
    },
    {
      "name": "payment_id",
      "postgres_type": "integer"
    },
    {
      "name": "refund_amount",
      "postgres_type": "numeric(15,2)"
    },
    {
      "name": "requested_at",
      "postgres_type": "timestamp without time zone"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "refund_id": 32,
        "payment_id": 94,
        "requested_at": "2025-07-19T01:50:00",
        "refund_amount": "634797.73"
      },
      {
        "refund_id": 27,
        "payment_id": 36,
        "requested_at": "2026-03-09T19:00:00",
        "refund_amount": "750171.09"
      },
      {
        "refund_id": 31,
        "payment_id": 87,
        "requested_at": "2026-08-12T00:20:00",
        "refund_amount": "267217.83"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "refunds"
  ],
  "process_wall_ms": 74.532,
  "oracle_row_count": 5,
  "result_sha256": "dfa8a81ece755f2757c96209c2ad362aa304be534b67ad2005008059b46e4dcd",
  "oracle_sha256": "dfa8a81ece755f2757c96209c2ad362aa304be534b67ad2005008059b46e4dcd",
  "repeat_runtime_ms": 4.863,
  "repeat_result_sha256": "dfa8a81ece755f2757c96209c2ad362aa304be534b67ad2005008059b46e4dcd",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Lọc hai điều kiện trực tiếp, không tính tiền ròng.",
    "primary_skill_group": "S1"
  }
}$ent_007_validation$::jsonb
);

-- ENT-008
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_008_question_id$ENT-008$ent_008_question_id$,
$ent_008_world_id$enterprise_v1$ent_008_world_id$,
$ent_008_title$Quốc gia trong mạng lưới nhà cung cấp$ent_008_title$,
$ent_008_question_text$Liệt kê country khác nhau, loại NULL, của toàn bộ nhà cung cấp không giới hạn status.
Cột kết quả theo thứ tự: country.
Sắp xếp: country tăng.
Quy tắc biên: Loại country IS NULL.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_008_question_text$,
$ent_008_reference_sql$SELECT DISTINCT country FROM suppliers WHERE country IS NOT NULL ORDER BY country;$ent_008_reference_sql$,
$ent_008_difficulty$easy$ent_008_difficulty$,
$ent_008_primary_skill_group$S1$ent_008_primary_skill_group$,
$ent_008_primary_business_domain$Product & Inventory$ent_008_primary_business_domain$,
$ent_008_skills$[]$ent_008_skills$::jsonb,
NULL,
$ent_008_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê country khác nhau, loại NULL, của toàn bộ nhà cung cấp không giới hạn status.",
  "output_grain": "Một quốc gia",
  "tables_used": [
    "suppliers"
  ],
  "difficulty_reason": "DISTINCT và loại NULL trực tiếp.",
  "order_by": "country tăng",
  "edge_cases": "Loại country IS NULL.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Quốc gia trong mạng lưới nhà cung cấp",
    "central_table": "suppliers",
    "grain": "Một quốc gia",
    "transformation": "distinct supplier countries nonnull",
    "predicate": "Liệt kê country khác nhau, loại NULL, của toàn bộ nhà cung cấp không giới hạn status.",
    "edge_cases": "Loại country IS NULL."
  },
  "output_columns": [
    {
      "name": "country",
      "meaning": "Quốc gia nhà cung cấp"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_008_metadata$::jsonb,
$ent_008_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 6,
  "runtime_ms": 2.341,
  "column_types": [
    {
      "name": "country",
      "postgres_type": "character varying(100)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "country": "Germany"
      },
      {
        "country": "Japan"
      },
      {
        "country": "Korea"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "suppliers"
  ],
  "process_wall_ms": 70.505,
  "oracle_row_count": 6,
  "result_sha256": "126a3762620fb50e2090c8d4be11a73a22792b29a1bbdb253da83f63c87040c8",
  "oracle_sha256": "126a3762620fb50e2090c8d4be11a73a22792b29a1bbdb253da83f63c87040c8",
  "repeat_runtime_ms": 2.452,
  "repeat_result_sha256": "126a3762620fb50e2090c8d4be11a73a22792b29a1bbdb253da83f63c87040c8",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "DISTINCT và loại NULL trực tiếp.",
    "primary_skill_group": "S1"
  }
}$ent_008_validation$::jsonb
);

-- ENT-009
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_009_question_id$ENT-009$ent_009_question_id$,
$ent_009_world_id$enterprise_v1$ent_009_world_id$,
$ent_009_title$Danh bạ địa chỉ mặc định$ent_009_title$,
$ent_009_question_text$Với mọi khách hàng, nối các địa chỉ is_default=true. Nếu không có thì vẫn giữ khách với các cột địa chỉ NULL.
Cột kết quả theo thứ tự: customer_id, full_name, address_id, city, address_line.
Sắp xếp: customer_id tăng, address_id tăng NULLS LAST.
Quy tắc biên: Nếu có nhiều địa chỉ mặc định thì giữ từng địa chỉ; không tự giả định unique.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_009_question_text$,
$ent_009_reference_sql$SELECT c.customer_id, c.full_name, a.address_id, a.city, a.address_line
FROM customers c LEFT JOIN customer_addresses a ON a.customer_id=c.customer_id AND a.is_default
ORDER BY c.customer_id, a.address_id NULLS LAST;$ent_009_reference_sql$,
$ent_009_difficulty$easy$ent_009_difficulty$,
$ent_009_primary_skill_group$S2$ent_009_primary_skill_group$,
$ent_009_primary_business_domain$Customer Management$ent_009_primary_business_domain$,
$ent_009_skills$[]$ent_009_skills$::jsonb,
NULL,
$ent_009_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Với mọi khách hàng, nối các địa chỉ is_default=true. Nếu không có thì vẫn giữ khách với các cột địa chỉ NULL.",
  "output_grain": "Một khách hàng và địa chỉ mặc định; một dòng NULL nếu không có",
  "tables_used": [
    "customers",
    "customer_addresses"
  ],
  "difficulty_reason": "Một LEFT JOIN trực tiếp với điều kiện địa chỉ mặc định.",
  "order_by": "customer_id tăng, address_id tăng NULLS LAST",
  "edge_cases": "Nếu có nhiều địa chỉ mặc định thì giữ từng địa chỉ; không tự giả định unique.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Danh bạ địa chỉ mặc định",
    "central_table": "customers",
    "grain": "Một khách hàng và địa chỉ mặc định; một dòng NULL nếu không có",
    "transformation": "left join default addresses preserving customers",
    "predicate": "Với mọi khách hàng, nối các địa chỉ is_default=true. Nếu không có thì vẫn giữ khách với các cột địa chỉ NULL.",
    "edge_cases": "Nếu có nhiều địa chỉ mặc định thì giữ từng địa chỉ; không tự giả định unique."
  },
  "output_columns": [
    {
      "name": "customer_id",
      "meaning": "Mã khách hàng"
    },
    {
      "name": "full_name",
      "meaning": "Họ tên được lưu"
    },
    {
      "name": "address_id",
      "meaning": "Mã địa chỉ"
    },
    {
      "name": "city",
      "meaning": "Thành phố của địa chỉ"
    },
    {
      "name": "address_line",
      "meaning": "Địa chỉ chi tiết"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_009_metadata$::jsonb,
$ent_009_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 300,
  "runtime_ms": 8.15,
  "column_types": [
    {
      "name": "customer_id",
      "postgres_type": "integer"
    },
    {
      "name": "full_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "address_id",
      "postgres_type": "integer"
    },
    {
      "name": "city",
      "postgres_type": "character varying(100)"
    },
    {
      "name": "address_line",
      "postgres_type": "character varying(255)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "city": "Hue",
        "full_name": "Pham Nam Customer 001",
        "address_id": 1,
        "customer_id": 1,
        "address_line": "11 Street 1"
      },
      {
        "city": "Hue",
        "full_name": "Le Chi Customer 002",
        "address_id": 2,
        "customer_id": 2,
        "address_line": "12 Street 1"
      },
      {
        "city": "Ho Chi Minh",
        "full_name": "Le Dung Customer 003",
        "address_id": 3,
        "customer_id": 3,
        "address_line": "13 Street 1"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "customer_addresses",
    "customers"
  ],
  "process_wall_ms": 186.645,
  "oracle_row_count": 300,
  "result_sha256": "7e6345078fbcf9e8a101d8e4c2a90419c19a48020d238263e6251e1c846055bf",
  "oracle_sha256": "7e6345078fbcf9e8a101d8e4c2a90419c19a48020d238263e6251e1c846055bf",
  "repeat_runtime_ms": 8.588,
  "repeat_result_sha256": "7e6345078fbcf9e8a101d8e4c2a90419c19a48020d238263e6251e1c846055bf",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Một LEFT JOIN trực tiếp với điều kiện địa chỉ mặc định.",
    "primary_skill_group": "S2"
  }
}$ent_009_validation$::jsonb
);

-- ENT-010
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_010_question_id$ENT-010$ent_010_question_id$,
$ent_010_world_id$enterprise_v1$ent_010_world_id$,
$ent_010_title$Tên sản phẩm trên từng dòng hàng$ent_010_title$,
$ent_010_question_text$Liệt kê mọi dòng order_items cùng tên sản phẩm, số lượng và line_total; không lọc trạng thái đơn.
Cột kết quả theo thứ tự: order_item_id, order_id, product_name, quantity, line_total.
Sắp xếp: order_item_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_010_question_text$,
$ent_010_reference_sql$SELECT i.order_item_id, i.order_id, p.product_name, i.quantity, i.line_total
FROM order_items i JOIN products p ON p.product_id=i.product_id ORDER BY i.order_item_id;$ent_010_reference_sql$,
$ent_010_difficulty$easy$ent_010_difficulty$,
$ent_010_primary_skill_group$S2$ent_010_primary_skill_group$,
$ent_010_primary_business_domain$Sales & Orders$ent_010_primary_business_domain$,
$ent_010_skills$[]$ent_010_skills$::jsonb,
NULL,
$ent_010_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê mọi dòng order_items cùng tên sản phẩm, số lượng và line_total; không lọc trạng thái đơn.",
  "output_grain": "Một dòng hàng",
  "tables_used": [
    "order_items",
    "products"
  ],
  "difficulty_reason": "Một JOIN qua khóa ngoại để bổ sung tên sản phẩm.",
  "order_by": "order_item_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Tên sản phẩm trên từng dòng hàng",
    "central_table": "order_items",
    "grain": "Một dòng hàng",
    "transformation": "line product lookup",
    "predicate": "Liệt kê mọi dòng order_items cùng tên sản phẩm, số lượng và line_total; không lọc trạng thái đơn.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "order_item_id",
      "meaning": "Mã dòng hàng"
    },
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "product_name",
      "meaning": "Tên sản phẩm"
    },
    {
      "name": "quantity",
      "meaning": "Số đơn vị trên dòng hàng"
    },
    {
      "name": "line_total",
      "meaning": "Giá trị dòng sau chiết khấu, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_010_metadata$::jsonb,
$ent_010_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 2892,
  "runtime_ms": 25.113,
  "column_types": [
    {
      "name": "order_item_id",
      "postgres_type": "integer"
    },
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "product_name",
      "postgres_type": "character varying(200)"
    },
    {
      "name": "quantity",
      "postgres_type": "integer"
    },
    {
      "name": "line_total",
      "postgres_type": "numeric(15,2)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "order_id": 1,
        "quantity": 1,
        "line_total": "664085.79",
        "product_name": "Product 015",
        "order_item_id": 1
      },
      {
        "order_id": 1,
        "quantity": 2,
        "line_total": "702391.98",
        "product_name": "Product 201",
        "order_item_id": 2
      },
      {
        "order_id": 1,
        "quantity": 3,
        "line_total": "1328599.72",
        "product_name": "Product 137",
        "order_item_id": 3
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "order_items",
    "products"
  ],
  "process_wall_ms": 99.861,
  "oracle_row_count": 2892,
  "result_sha256": "f8c990e36372caca2d00924a13777c5da9d6cf90e19e929ef4c2d0ec4980c279",
  "oracle_sha256": "f8c990e36372caca2d00924a13777c5da9d6cf90e19e929ef4c2d0ec4980c279",
  "repeat_runtime_ms": 26.007,
  "repeat_result_sha256": "f8c990e36372caca2d00924a13777c5da9d6cf90e19e929ef4c2d0ec4980c279",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Một JOIN qua khóa ngoại để bổ sung tên sản phẩm.",
    "primary_skill_group": "S2"
  }
}$ent_010_validation$::jsonb
);

-- ENT-011
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_011_question_id$ENT-011$ent_011_question_id$,
$ent_011_world_id$enterprise_v1$ent_011_world_id$,
$ent_011_title$Danh mục trực tiếp của sản phẩm$ent_011_title$,
$ent_011_question_text$Liệt kê sản phẩm với tên danh mục trực tiếp và trạng thái is_active của danh mục, không duyệt cha.
Cột kết quả theo thứ tự: product_id, product_name, category_name, category_active.
Sắp xếp: product_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_011_question_text$,
$ent_011_reference_sql$SELECT p.product_id, p.product_name, c.category_name, c.is_active AS category_active
FROM products p JOIN categories c ON c.category_id=p.category_id ORDER BY p.product_id;$ent_011_reference_sql$,
$ent_011_difficulty$easy$ent_011_difficulty$,
$ent_011_primary_skill_group$S2$ent_011_primary_skill_group$,
$ent_011_primary_business_domain$Product & Inventory$ent_011_primary_business_domain$,
$ent_011_skills$[]$ent_011_skills$::jsonb,
NULL,
$ent_011_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê sản phẩm với tên danh mục trực tiếp và trạng thái is_active của danh mục, không duyệt cha.",
  "output_grain": "Một sản phẩm",
  "tables_used": [
    "products",
    "categories"
  ],
  "difficulty_reason": "Nối trực tiếp sản phẩm với danh mục.",
  "order_by": "product_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Danh mục trực tiếp của sản phẩm",
    "central_table": "products",
    "grain": "Một sản phẩm",
    "transformation": "product direct category lookup",
    "predicate": "Liệt kê sản phẩm với tên danh mục trực tiếp và trạng thái is_active của danh mục, không duyệt cha.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "product_id",
      "meaning": "Mã sản phẩm"
    },
    {
      "name": "product_name",
      "meaning": "Tên sản phẩm"
    },
    {
      "name": "category_name",
      "meaning": "Tên danh mục trực tiếp"
    },
    {
      "name": "category_active",
      "meaning": "Danh mục trực tiếp còn hoạt động"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_011_metadata$::jsonb,
$ent_011_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 250,
  "runtime_ms": 5.902,
  "column_types": [
    {
      "name": "product_id",
      "postgres_type": "integer"
    },
    {
      "name": "product_name",
      "postgres_type": "character varying(200)"
    },
    {
      "name": "category_name",
      "postgres_type": "character varying(100)"
    },
    {
      "name": "category_active",
      "postgres_type": "boolean"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "product_id": 1,
        "product_name": "Product 001",
        "category_name": "Sports 3",
        "category_active": true
      },
      {
        "product_id": 2,
        "product_name": "Product 002",
        "category_name": "Fashion",
        "category_active": true
      },
      {
        "product_id": 3,
        "product_name": "Product 003",
        "category_name": "Fashion 3",
        "category_active": true
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "categories",
    "products"
  ],
  "process_wall_ms": 75.377,
  "oracle_row_count": 250,
  "result_sha256": "b08c1c6678860e37169f38695bf2ad7e1a0e1f4f85f2f89d7ba1869a0c4e305f",
  "oracle_sha256": "b08c1c6678860e37169f38695bf2ad7e1a0e1f4f85f2f89d7ba1869a0c4e305f",
  "repeat_runtime_ms": 6.613,
  "repeat_result_sha256": "b08c1c6678860e37169f38695bf2ad7e1a0e1f4f85f2f89d7ba1869a0c4e305f",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Nối trực tiếp sản phẩm với danh mục.",
    "primary_skill_group": "S2"
  }
}$ent_011_validation$::jsonb
);

-- ENT-012
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_012_question_id$ENT-012$ent_012_question_id$,
$ent_012_world_id$enterprise_v1$ent_012_world_id$,
$ent_012_title$Liên hệ nguồn cung cho sản phẩm$ent_012_title$,
$ent_012_question_text$Liệt kê sản phẩm, nhà cung cấp, quốc gia và email liên hệ; giữ email hoặc quốc gia NULL.
Cột kết quả theo thứ tự: product_id, sku, supplier_name, country, contact_email.
Sắp xếp: product_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_012_question_text$,
$ent_012_reference_sql$SELECT p.product_id, p.sku, s.supplier_name, s.country, s.contact_email
FROM products p JOIN suppliers s ON s.supplier_id=p.supplier_id ORDER BY p.product_id;$ent_012_reference_sql$,
$ent_012_difficulty$easy$ent_012_difficulty$,
$ent_012_primary_skill_group$S2$ent_012_primary_skill_group$,
$ent_012_primary_business_domain$Product & Inventory$ent_012_primary_business_domain$,
$ent_012_skills$[]$ent_012_skills$::jsonb,
NULL,
$ent_012_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê sản phẩm, nhà cung cấp, quốc gia và email liên hệ; giữ email hoặc quốc gia NULL.",
  "output_grain": "Một sản phẩm",
  "tables_used": [
    "products",
    "suppliers"
  ],
  "difficulty_reason": "Một JOIN để tra cứu quan hệ nguồn cung.",
  "order_by": "product_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Liên hệ nguồn cung cho sản phẩm",
    "central_table": "products",
    "grain": "Một sản phẩm",
    "transformation": "product supplier contact lookup",
    "predicate": "Liệt kê sản phẩm, nhà cung cấp, quốc gia và email liên hệ; giữ email hoặc quốc gia NULL.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "product_id",
      "meaning": "Mã sản phẩm"
    },
    {
      "name": "sku",
      "meaning": "Mã SKU của sản phẩm"
    },
    {
      "name": "supplier_name",
      "meaning": "Tên nhà cung cấp"
    },
    {
      "name": "country",
      "meaning": "Quốc gia nhà cung cấp"
    },
    {
      "name": "contact_email",
      "meaning": "Email liên hệ nhà cung cấp, có thể NULL"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_012_metadata$::jsonb,
$ent_012_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 250,
  "runtime_ms": 7.59,
  "column_types": [
    {
      "name": "product_id",
      "postgres_type": "integer"
    },
    {
      "name": "sku",
      "postgres_type": "character varying(50)"
    },
    {
      "name": "supplier_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "country",
      "postgres_type": "character varying(100)"
    },
    {
      "name": "contact_email",
      "postgres_type": "character varying(255)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "sku": "SKU-00001",
        "country": "Germany",
        "product_id": 1,
        "contact_email": "supplier04@supply.example",
        "supplier_name": "Supplier 04"
      },
      {
        "sku": "SKU-00002",
        "country": "Japan",
        "product_id": 2,
        "contact_email": "supplier13@supply.example",
        "supplier_name": "Supplier 13"
      },
      {
        "sku": "SKU-00003",
        "country": "Germany",
        "product_id": 3,
        "contact_email": "supplier23@supply.example",
        "supplier_name": "Supplier 23"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "products",
    "suppliers"
  ],
  "process_wall_ms": 74.076,
  "oracle_row_count": 250,
  "result_sha256": "72549f24938208b578b54b835e79344707bc9f5600b222e3446c6c7580f5e2a0",
  "oracle_sha256": "72549f24938208b578b54b835e79344707bc9f5600b222e3446c6c7580f5e2a0",
  "repeat_runtime_ms": 7.078,
  "repeat_result_sha256": "72549f24938208b578b54b835e79344707bc9f5600b222e3446c6c7580f5e2a0",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Một JOIN để tra cứu quan hệ nguồn cung.",
    "primary_skill_group": "S2"
  }
}$ent_012_validation$::jsonb
);

-- ENT-013
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_013_question_id$ENT-013$ent_013_question_id$,
$ent_013_world_id$enterprise_v1$ent_013_world_id$,
$ent_013_title$Danh bạ nhân viên và quản lý trực tiếp$ent_013_title$,
$ent_013_question_text$Liệt kê mọi nhân viên cùng ID và tên quản lý trực tiếp; nhân viên gốc vẫn xuất hiện.
Cột kết quả theo thứ tự: employee_id, employee_name, manager_id, manager_name.
Sắp xếp: employee_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_013_question_text$,
$ent_013_reference_sql$SELECT e.employee_id, e.full_name AS employee_name, e.manager_id, m.full_name AS manager_name
FROM employees e LEFT JOIN employees m ON m.employee_id=e.manager_id ORDER BY e.employee_id;$ent_013_reference_sql$,
$ent_013_difficulty$easy$ent_013_difficulty$,
$ent_013_primary_skill_group$S2$ent_013_primary_skill_group$,
$ent_013_primary_business_domain$Human Resources$ent_013_primary_business_domain$,
$ent_013_skills$[]$ent_013_skills$::jsonb,
NULL,
$ent_013_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê mọi nhân viên cùng ID và tên quản lý trực tiếp; nhân viên gốc vẫn xuất hiện.",
  "output_grain": "Một nhân viên",
  "tables_used": [
    "employees"
  ],
  "difficulty_reason": "SELF LEFT JOIN một cấp, không đệ quy.",
  "order_by": "employee_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Danh bạ nhân viên và quản lý trực tiếp",
    "central_table": "employees",
    "grain": "Một nhân viên",
    "transformation": "self left join immediate manager",
    "predicate": "Liệt kê mọi nhân viên cùng ID và tên quản lý trực tiếp; nhân viên gốc vẫn xuất hiện.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "employee_id",
      "meaning": "Mã nhân viên"
    },
    {
      "name": "employee_name",
      "meaning": "Tên nhân viên"
    },
    {
      "name": "manager_id",
      "meaning": "Mã quản lý trực tiếp, có thể NULL"
    },
    {
      "name": "manager_name",
      "meaning": "Tên quản lý ở vai trò được hỏi"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_013_metadata$::jsonb,
$ent_013_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 100,
  "runtime_ms": 5.701,
  "column_types": [
    {
      "name": "employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "employee_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "manager_id",
      "postgres_type": "integer"
    },
    {
      "name": "manager_name",
      "postgres_type": "character varying(150)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "manager_id": null,
        "employee_id": 1,
        "manager_name": null,
        "employee_name": "Nguyen Hung Employee 001"
      },
      {
        "manager_id": null,
        "employee_id": 2,
        "manager_name": null,
        "employee_name": "Tran Lan Employee 002"
      },
      {
        "manager_id": null,
        "employee_id": 3,
        "manager_name": null,
        "employee_name": "Do Lan Employee 003"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "employees"
  ],
  "process_wall_ms": 77.585,
  "oracle_row_count": 100,
  "result_sha256": "e415c76f0633f9f50ab6b4e2e7ccff64834927fd01662d534ec6f691a64cf9b4",
  "oracle_sha256": "e415c76f0633f9f50ab6b4e2e7ccff64834927fd01662d534ec6f691a64cf9b4",
  "repeat_runtime_ms": 3.929,
  "repeat_result_sha256": "e415c76f0633f9f50ab6b4e2e7ccff64834927fd01662d534ec6f691a64cf9b4",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "SELF LEFT JOIN một cấp, không đệ quy.",
    "primary_skill_group": "S2"
  }
}$ent_013_validation$::jsonb
);

-- ENT-014
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_014_question_id$ENT-014$ent_014_question_id$,
$ent_014_world_id$enterprise_v1$ent_014_world_id$,
$ent_014_title$Trưởng phòng được chỉ định$ent_014_title$,
$ent_014_question_text$Liệt kê tất cả phòng ban và nhân viên được manager_employee_id chỉ định, không suy từ manager_id.
Cột kết quả theo thứ tự: department_id, department_name, manager_employee_id, manager_name.
Sắp xếp: department_id tăng.
Quy tắc biên: Phòng chưa chỉ định trưởng phòng vẫn xuất hiện với manager_name NULL.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_014_question_text$,
$ent_014_reference_sql$SELECT d.department_id, d.department_name, d.manager_employee_id, e.full_name AS manager_name
FROM departments d LEFT JOIN employees e ON e.employee_id=d.manager_employee_id ORDER BY d.department_id;$ent_014_reference_sql$,
$ent_014_difficulty$easy$ent_014_difficulty$,
$ent_014_primary_skill_group$S2$ent_014_primary_skill_group$,
$ent_014_primary_business_domain$Human Resources$ent_014_primary_business_domain$,
$ent_014_skills$[]$ent_014_skills$::jsonb,
NULL,
$ent_014_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê tất cả phòng ban và nhân viên được manager_employee_id chỉ định, không suy từ manager_id.",
  "output_grain": "Một phòng ban",
  "tables_used": [
    "departments",
    "employees"
  ],
  "difficulty_reason": "Một LEFT JOIN trực tiếp theo khóa trưởng phòng.",
  "order_by": "department_id tăng",
  "edge_cases": "Phòng chưa chỉ định trưởng phòng vẫn xuất hiện với manager_name NULL.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Trưởng phòng được chỉ định",
    "central_table": "departments",
    "grain": "Một phòng ban",
    "transformation": "department designated manager left lookup",
    "predicate": "Liệt kê tất cả phòng ban và nhân viên được manager_employee_id chỉ định, không suy từ manager_id.",
    "edge_cases": "Phòng chưa chỉ định trưởng phòng vẫn xuất hiện với manager_name NULL."
  },
  "output_columns": [
    {
      "name": "department_id",
      "meaning": "Mã phòng hiện tại"
    },
    {
      "name": "department_name",
      "meaning": "Tên phòng ban"
    },
    {
      "name": "manager_employee_id",
      "meaning": "Mã trưởng phòng được chỉ định"
    },
    {
      "name": "manager_name",
      "meaning": "Tên quản lý ở vai trò được hỏi"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_014_metadata$::jsonb,
$ent_014_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 5.624,
  "column_types": [
    {
      "name": "department_id",
      "postgres_type": "integer"
    },
    {
      "name": "department_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "manager_employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "manager_name",
      "postgres_type": "character varying(150)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "manager_name": "Nguyen Hung Employee 001",
        "department_id": 1,
        "department_name": "Sales",
        "manager_employee_id": 1
      },
      {
        "manager_name": "Tran Lan Employee 002",
        "department_id": 2,
        "department_name": "Marketing",
        "manager_employee_id": 2
      },
      {
        "manager_name": "Do Lan Employee 003",
        "department_id": 3,
        "department_name": "Operations",
        "manager_employee_id": 3
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "departments",
    "employees"
  ],
  "process_wall_ms": 79.215,
  "oracle_row_count": 8,
  "result_sha256": "9f8ad0181f5149f0cb9d8f91c57079eca70d82a28cb3ab16cae900e53b7b7ffd",
  "oracle_sha256": "9f8ad0181f5149f0cb9d8f91c57079eca70d82a28cb3ab16cae900e53b7b7ffd",
  "repeat_runtime_ms": 5.256,
  "repeat_result_sha256": "9f8ad0181f5149f0cb9d8f91c57079eca70d82a28cb3ab16cae900e53b7b7ffd",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Một LEFT JOIN trực tiếp theo khóa trưởng phòng.",
    "primary_skill_group": "S2"
  }
}$ent_014_validation$::jsonb
);

-- ENT-015
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_015_question_id$ENT-015$ent_015_question_id$,
$ent_015_world_id$enterprise_v1$ent_015_world_id$,
$ent_015_title$Người phê duyệt từng khoản chi$ent_015_title$,
$ent_015_question_text$Liệt kê mọi khoản operating_expenses và tên người phê duyệt; khoản chưa có người phê duyệt vẫn xuất hiện.
Cột kết quả theo thứ tự: expense_id, expense_category, amount, expense_date, approver_name.
Sắp xếp: expense_id tăng.
Quy tắc biên: Không có approved_at; expense_date không được gọi là ngày phê duyệt.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_015_question_text$,
$ent_015_reference_sql$SELECT x.expense_id, x.expense_category, x.amount, x.expense_date, e.full_name AS approver_name
FROM operating_expenses x LEFT JOIN employees e ON e.employee_id=x.approved_by_employee_id ORDER BY x.expense_id;$ent_015_reference_sql$,
$ent_015_difficulty$easy$ent_015_difficulty$,
$ent_015_primary_skill_group$S2$ent_015_primary_skill_group$,
$ent_015_primary_business_domain$Finance$ent_015_primary_business_domain$,
$ent_015_skills$[]$ent_015_skills$::jsonb,
NULL,
$ent_015_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê mọi khoản operating_expenses và tên người phê duyệt; khoản chưa có người phê duyệt vẫn xuất hiện.",
  "output_grain": "Một khoản chi",
  "tables_used": [
    "operating_expenses",
    "employees"
  ],
  "difficulty_reason": "Một LEFT JOIN để đọc quan hệ phê duyệt.",
  "order_by": "expense_id tăng",
  "edge_cases": "Không có approved_at; expense_date không được gọi là ngày phê duyệt.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Người phê duyệt từng khoản chi",
    "central_table": "operating_expenses",
    "grain": "Một khoản chi",
    "transformation": "expense optional approver lookup",
    "predicate": "Liệt kê mọi khoản operating_expenses và tên người phê duyệt; khoản chưa có người phê duyệt vẫn xuất hiện.",
    "edge_cases": "Không có approved_at; expense_date không được gọi là ngày phê duyệt."
  },
  "output_columns": [
    {
      "name": "expense_id",
      "meaning": "Mã khoản chi"
    },
    {
      "name": "expense_category",
      "meaning": "Loại chi phí"
    },
    {
      "name": "amount",
      "meaning": "Giá trị khoản chi, VND"
    },
    {
      "name": "expense_date",
      "meaning": "Ngày phát sinh chi phí"
    },
    {
      "name": "approver_name",
      "meaning": "Tên người phê duyệt, có thể NULL"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_015_metadata$::jsonb,
$ent_015_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 240,
  "runtime_ms": 6.51,
  "column_types": [
    {
      "name": "expense_id",
      "postgres_type": "integer"
    },
    {
      "name": "expense_category",
      "postgres_type": "character varying(100)"
    },
    {
      "name": "amount",
      "postgres_type": "numeric(15,2)"
    },
    {
      "name": "expense_date",
      "postgres_type": "date"
    },
    {
      "name": "approver_name",
      "postgres_type": "character varying(150)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "amount": "1926000.00",
        "expense_id": 1,
        "expense_date": "2021-12-23",
        "approver_name": "Le Lan Employee 086",
        "expense_category": "Training"
      },
      {
        "amount": "1899000.00",
        "expense_id": 2,
        "expense_date": "2024-10-17",
        "approver_name": "Tran Nam Employee 063",
        "expense_category": "Rent"
      },
      {
        "amount": "4432000.00",
        "expense_id": 3,
        "expense_date": "2023-03-21",
        "approver_name": "Vu An Employee 085",
        "expense_category": "Office supplies"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "employees",
    "operating_expenses"
  ],
  "process_wall_ms": 76.902,
  "oracle_row_count": 240,
  "result_sha256": "153a9e460bfba2925b4293b0eab61e05d45ad7ea5028316979bfdb7d4897acaa",
  "oracle_sha256": "153a9e460bfba2925b4293b0eab61e05d45ad7ea5028316979bfdb7d4897acaa",
  "repeat_runtime_ms": 7.029,
  "repeat_result_sha256": "153a9e460bfba2925b4293b0eab61e05d45ad7ea5028316979bfdb7d4897acaa",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Một LEFT JOIN để đọc quan hệ phê duyệt.",
    "primary_skill_group": "S2"
  }
}$ent_015_validation$::jsonb
);

-- ENT-016
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_016_question_id$ENT-016$ent_016_question_id$,
$ent_016_world_id$enterprise_v1$ent_016_world_id$,
$ent_016_title$Quy mô khách hàng theo trạng thái$ent_016_title$,
$ent_016_question_text$Đếm khách hàng theo status; mỗi khách chỉ đếm một lần.
Cột kết quả theo thứ tự: status, customer_count.
Sắp xếp: status tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_016_question_text$,
$ent_016_reference_sql$SELECT status, COUNT(*) AS customer_count FROM customers GROUP BY status ORDER BY status;$ent_016_reference_sql$,
$ent_016_difficulty$easy$ent_016_difficulty$,
$ent_016_primary_skill_group$S3$ent_016_primary_skill_group$,
$ent_016_primary_business_domain$Customer Management$ent_016_primary_business_domain$,
$ent_016_skills$[]$ent_016_skills$::jsonb,
NULL,
$ent_016_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Đếm khách hàng theo status; mỗi khách chỉ đếm một lần.",
  "output_grain": "Một trạng thái khách hàng",
  "tables_used": [
    "customers"
  ],
  "difficulty_reason": "GROUP BY và COUNT đơn giản trên một bảng.",
  "order_by": "status tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Quy mô khách hàng theo trạng thái",
    "central_table": "customers",
    "grain": "Một trạng thái khách hàng",
    "transformation": "group customer status count",
    "predicate": "Đếm khách hàng theo status; mỗi khách chỉ đếm một lần.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "status",
      "meaning": "Trạng thái của đối tượng được nhóm hoặc lọc trong đề"
    },
    {
      "name": "customer_count",
      "meaning": "Số khách hàng"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_016_metadata$::jsonb,
$ent_016_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 2,
  "runtime_ms": 4.013,
  "column_types": [
    {
      "name": "status",
      "postgres_type": "character varying(20)"
    },
    {
      "name": "customer_count",
      "postgres_type": "bigint"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "status": "active",
        "customer_count": 273
      },
      {
        "status": "inactive",
        "customer_count": 27
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "customers"
  ],
  "process_wall_ms": 82.375,
  "oracle_row_count": 2,
  "result_sha256": "d4bdb9609f3ea5f043348fc440907e88a9cade9c41801d2482550228ac34dced",
  "oracle_sha256": "d4bdb9609f3ea5f043348fc440907e88a9cade9c41801d2482550228ac34dced",
  "repeat_runtime_ms": 5.138,
  "repeat_result_sha256": "d4bdb9609f3ea5f043348fc440907e88a9cade9c41801d2482550228ac34dced",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "GROUP BY và COUNT đơn giản trên một bảng.",
    "primary_skill_group": "S3"
  }
}$ent_016_validation$::jsonb
);

-- ENT-017
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_017_question_id$ENT-017$ent_017_question_id$,
$ent_017_world_id$enterprise_v1$ent_017_world_id$,
$ent_017_title$Giá trị đơn hàng theo trạng thái$ent_017_title$,
$ent_017_question_text$Theo status của đơn, tính số đơn và tổng total_amount. Đây là giá trị đơn gồm phí giao hàng, không phải tiền đã thu.
Cột kết quả theo thứ tự: status, order_count, order_value.
Sắp xếp: status tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_017_question_text$,
$ent_017_reference_sql$SELECT status, COUNT(*) AS order_count, SUM(total_amount) AS order_value
FROM orders GROUP BY status ORDER BY status;$ent_017_reference_sql$,
$ent_017_difficulty$easy$ent_017_difficulty$,
$ent_017_primary_skill_group$S3$ent_017_primary_skill_group$,
$ent_017_primary_business_domain$Sales & Orders$ent_017_primary_business_domain$,
$ent_017_skills$[]$ent_017_skills$::jsonb,
NULL,
$ent_017_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Theo status của đơn, tính số đơn và tổng total_amount. Đây là giá trị đơn gồm phí giao hàng, không phải tiền đã thu.",
  "output_grain": "Một trạng thái đơn hàng",
  "tables_used": [
    "orders"
  ],
  "difficulty_reason": "Một bước nhóm và tổng hợp trên orders.",
  "order_by": "status tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Giá trị đơn hàng theo trạng thái",
    "central_table": "orders",
    "grain": "Một trạng thái đơn hàng",
    "transformation": "group status count sum order value",
    "predicate": "Theo status của đơn, tính số đơn và tổng total_amount. Đây là giá trị đơn gồm phí giao hàng, không phải tiền đã thu.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "status",
      "meaning": "Trạng thái của đối tượng được nhóm hoặc lọc trong đề"
    },
    {
      "name": "order_count",
      "meaning": "Số đơn hàng"
    },
    {
      "name": "order_value",
      "meaning": "Tổng giá trị đơn, không phải tiền thực thu, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_017_metadata$::jsonb,
$ent_017_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 5,
  "runtime_ms": 3.996,
  "column_types": [
    {
      "name": "status",
      "postgres_type": "character varying(30)"
    },
    {
      "name": "order_count",
      "postgres_type": "bigint"
    },
    {
      "name": "order_value",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "status": "cancelled",
        "order_count": 100,
        "order_value": "344322483.72"
      },
      {
        "status": "delivered",
        "order_count": 390,
        "order_value": "1451103857.42"
      },
      {
        "status": "pending",
        "order_count": 110,
        "order_value": "395777560.05"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "orders"
  ],
  "process_wall_ms": 73.811,
  "oracle_row_count": 5,
  "result_sha256": "b318f218d86a2f1af6e3456776096424d48f6ab98682472cd63529432591ba54",
  "oracle_sha256": "b318f218d86a2f1af6e3456776096424d48f6ab98682472cd63529432591ba54",
  "repeat_runtime_ms": 5.183,
  "repeat_result_sha256": "b318f218d86a2f1af6e3456776096424d48f6ab98682472cd63529432591ba54",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Một bước nhóm và tổng hợp trên orders.",
    "primary_skill_group": "S3"
  }
}$ent_017_validation$::jsonb
);

-- ENT-018
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_018_question_id$ENT-018$ent_018_question_id$,
$ent_018_world_id$enterprise_v1$ent_018_world_id$,
$ent_018_title$Tổng biến động theo loại giao dịch kho$ent_018_title$,
$ent_018_question_text$Theo transaction_type, tính số giao dịch và tổng quantity_change có dấu, trên toàn bộ kho và thời gian.
Cột kết quả theo thứ tự: transaction_type, transaction_count, net_units.
Sắp xếp: transaction_type tăng.
Quy tắc biên: sale có tổng âm; không lấy trị tuyệt đối.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_018_question_text$,
$ent_018_reference_sql$SELECT transaction_type, COUNT(*) AS transaction_count, SUM(quantity_change) AS net_units
FROM inventory_transactions GROUP BY transaction_type ORDER BY transaction_type;$ent_018_reference_sql$,
$ent_018_difficulty$easy$ent_018_difficulty$,
$ent_018_primary_skill_group$S3$ent_018_primary_skill_group$,
$ent_018_primary_business_domain$Product & Inventory$ent_018_primary_business_domain$,
$ent_018_skills$[]$ent_018_skills$::jsonb,
NULL,
$ent_018_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Theo transaction_type, tính số giao dịch và tổng quantity_change có dấu, trên toàn bộ kho và thời gian.",
  "output_grain": "Một loại giao dịch",
  "tables_used": [
    "inventory_transactions"
  ],
  "difficulty_reason": "Tổng hợp một bảng; không tính tồn tích lũy.",
  "order_by": "transaction_type tăng",
  "edge_cases": "sale có tổng âm; không lấy trị tuyệt đối.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Tổng biến động theo loại giao dịch kho",
    "central_table": "inventory_transactions",
    "grain": "Một loại giao dịch",
    "transformation": "group inventory type signed movement sum",
    "predicate": "Theo transaction_type, tính số giao dịch và tổng quantity_change có dấu, trên toàn bộ kho và thời gian.",
    "edge_cases": "sale có tổng âm; không lấy trị tuyệt đối."
  },
  "output_columns": [
    {
      "name": "transaction_type",
      "meaning": "Loại biến động kho"
    },
    {
      "name": "transaction_count",
      "meaning": "Số giao dịch kho"
    },
    {
      "name": "net_units",
      "meaning": "Tổng biến động số lượng có dấu"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_018_metadata$::jsonb,
$ent_018_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 3,
  "runtime_ms": 8.12,
  "column_types": [
    {
      "name": "transaction_type",
      "postgres_type": "character varying(30)"
    },
    {
      "name": "transaction_count",
      "postgres_type": "bigint"
    },
    {
      "name": "net_units",
      "postgres_type": "bigint"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "net_units": 94119,
        "transaction_type": "import",
        "transaction_count": 1198
      },
      {
        "net_units": 285,
        "transaction_type": "return",
        "transaction_count": 103
      },
      {
        "net_units": -4827,
        "transaction_type": "sale",
        "transaction_count": 1859
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "inventory_transactions"
  ],
  "process_wall_ms": 85.355,
  "oracle_row_count": 3,
  "result_sha256": "6b947949a00bfedaf7e831ede57a4bfe14c1e50c665478eabbf70ce8aa0af448",
  "oracle_sha256": "6b947949a00bfedaf7e831ede57a4bfe14c1e50c665478eabbf70ce8aa0af448",
  "repeat_runtime_ms": 4.875,
  "repeat_result_sha256": "6b947949a00bfedaf7e831ede57a4bfe14c1e50c665478eabbf70ce8aa0af448",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Tổng hợp một bảng; không tính tồn tích lũy.",
    "primary_skill_group": "S3"
  }
}$ent_018_validation$::jsonb
);

-- ENT-019
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_019_question_id$ENT-019$ent_019_question_id$,
$ent_019_world_id$enterprise_v1$ent_019_world_id$,
$ent_019_title$Quỹ lương hiện tại theo mã phòng$ent_019_title$,
$ent_019_question_text$Theo department_id của nhân viên, tính số nhân viên và tổng current_salary, không lọc status.
Cột kết quả theo thứ tự: department_id, employee_count, current_payroll.
Sắp xếp: department_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_019_question_text$,
$ent_019_reference_sql$SELECT department_id, COUNT(*) AS employee_count, SUM(current_salary) AS current_payroll
FROM employees GROUP BY department_id ORDER BY department_id;$ent_019_reference_sql$,
$ent_019_difficulty$easy$ent_019_difficulty$,
$ent_019_primary_skill_group$S3$ent_019_primary_skill_group$,
$ent_019_primary_business_domain$Human Resources$ent_019_primary_business_domain$,
$ent_019_skills$[]$ent_019_skills$::jsonb,
NULL,
$ent_019_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Theo department_id của nhân viên, tính số nhân viên và tổng current_salary, không lọc status.",
  "output_grain": "Một mã phòng có nhân viên",
  "tables_used": [
    "employees"
  ],
  "difficulty_reason": "Một bước tổng hợp lương hiện tại, không suy lương lịch sử.",
  "order_by": "department_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Quỹ lương hiện tại theo mã phòng",
    "central_table": "employees",
    "grain": "Một mã phòng có nhân viên",
    "transformation": "group department present salary sum",
    "predicate": "Theo department_id của nhân viên, tính số nhân viên và tổng current_salary, không lọc status.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "department_id",
      "meaning": "Mã phòng hiện tại"
    },
    {
      "name": "employee_count",
      "meaning": "Số nhân viên"
    },
    {
      "name": "current_payroll",
      "meaning": "Tổng lương hiện tại, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_019_metadata$::jsonb,
$ent_019_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 3.385,
  "column_types": [
    {
      "name": "department_id",
      "postgres_type": "integer"
    },
    {
      "name": "employee_count",
      "postgres_type": "bigint"
    },
    {
      "name": "current_payroll",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "department_id": 1,
        "employee_count": 13,
        "current_payroll": "390000000.00"
      },
      {
        "department_id": 2,
        "employee_count": 13,
        "current_payroll": "378000000.00"
      },
      {
        "department_id": 3,
        "employee_count": 13,
        "current_payroll": "373000000.00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "employees"
  ],
  "process_wall_ms": 80.366,
  "oracle_row_count": 8,
  "result_sha256": "3783c141c4999e95d28e893f9a5d74f800b0364a4063e24ef2ba99b316e2acf3",
  "oracle_sha256": "3783c141c4999e95d28e893f9a5d74f800b0364a4063e24ef2ba99b316e2acf3",
  "repeat_runtime_ms": 3.969,
  "repeat_result_sha256": "3783c141c4999e95d28e893f9a5d74f800b0364a4063e24ef2ba99b316e2acf3",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Một bước tổng hợp lương hiện tại, không suy lương lịch sử.",
    "primary_skill_group": "S3"
  }
}$ent_019_validation$::jsonb
);

-- ENT-020
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_020_question_id$ENT-020$ent_020_question_id$,
$ent_020_world_id$enterprise_v1$ent_020_world_id$,
$ent_020_title$Thời gian xử lý hoàn tiền đã hoàn tất$ent_020_title$,
$ent_020_question_text$Trong refund_status='completed' có completed_at không NULL, tính số yêu cầu và thời gian xử lý ngắn nhất, dài nhất, trung bình bằng giờ từ requested_at đến completed_at. Làm tròn các số giờ 2 chữ số.
Cột kết quả theo thứ tự: completed_refunds, min_hours, max_hours, avg_hours.
Sắp xếp: Một dòng nên không có yêu cầu thứ tự.
Quy tắc biên: Nếu không có refund hoàn tất thì số yêu cầu=0 và các số giờ=NULL.
Thời gian: completed_at-requested_at; không dùng attempted_at.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_020_question_text$,
$ent_020_reference_sql$SELECT COUNT(*) AS completed_refunds,
 ROUND(MIN(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS min_hours,
 ROUND(MAX(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS max_hours,
 ROUND(AVG(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS avg_hours
FROM refunds WHERE refund_status='completed' AND completed_at IS NOT NULL;$ent_020_reference_sql$,
$ent_020_difficulty$easy$ent_020_difficulty$,
$ent_020_primary_skill_group$S3$ent_020_primary_skill_group$,
$ent_020_primary_business_domain$Finance$ent_020_primary_business_domain$,
$ent_020_skills$[]$ent_020_skills$::jsonb,
NULL,
$ent_020_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Trong refund_status='completed' có completed_at không NULL, tính số yêu cầu và thời gian xử lý ngắn nhất, dài nhất, trung bình bằng giờ từ requested_at đến completed_at. Làm tròn các số giờ 2 chữ số.",
  "output_grain": "Một dòng thống kê toàn bộ refund hoàn tất",
  "tables_used": [
    "refunds"
  ],
  "difficulty_reason": "Tổng hợp trực tiếp độ dài thời gian trên một bảng, không ghép lịch sử sự kiện.",
  "order_by": "Một dòng nên không có yêu cầu thứ tự",
  "edge_cases": "Nếu không có refund hoàn tất thì số yêu cầu=0 và các số giờ=NULL.",
  "time_basis": "completed_at-requested_at; không dùng attempted_at.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Thời gian xử lý hoàn tiền đã hoàn tất",
    "central_table": "refunds",
    "grain": "Một dòng thống kê toàn bộ refund hoàn tất",
    "transformation": "completed refund turnaround global min max average hours",
    "predicate": "Trong refund_status='completed' có completed_at không NULL, tính số yêu cầu và thời gian xử lý ngắn nhất, dài nhất, trung bình bằng giờ từ requested_at đến completed_at. Làm tròn các số giờ 2 chữ số.",
    "edge_cases": "Nếu không có refund hoàn tất thì số yêu cầu=0 và các số giờ=NULL."
  },
  "output_columns": [
    {
      "name": "completed_refunds",
      "meaning": "Số yêu cầu hoàn tiền completed có ngày hoàn tất"
    },
    {
      "name": "min_hours",
      "meaning": "Số giờ xử lý ngắn nhất"
    },
    {
      "name": "max_hours",
      "meaning": "Số giờ xử lý dài nhất"
    },
    {
      "name": "avg_hours",
      "meaning": "Số giờ xử lý trung bình"
    }
  ],
  "money_unit": "VND",
  "ordering_required": false
}$ent_020_metadata$::jsonb,
$ent_020_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 1,
  "runtime_ms": 3.833,
  "column_types": [
    {
      "name": "completed_refunds",
      "postgres_type": "bigint"
    },
    {
      "name": "min_hours",
      "postgres_type": "numeric"
    },
    {
      "name": "max_hours",
      "postgres_type": "numeric"
    },
    {
      "name": "avg_hours",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "avg_hours": "48.00",
        "max_hours": "48.00",
        "min_hours": "48.00",
        "completed_refunds": 25
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "refunds"
  ],
  "process_wall_ms": 73.179,
  "oracle_row_count": 1,
  "result_sha256": "ac62c6e9430a099fbbf261d380db724a2fee8f23d09b2fddce4206da3894ef84",
  "oracle_sha256": "ac62c6e9430a099fbbf261d380db724a2fee8f23d09b2fddce4206da3894ef84",
  "repeat_runtime_ms": 3.798,
  "repeat_result_sha256": "ac62c6e9430a099fbbf261d380db724a2fee8f23d09b2fddce4206da3894ef84",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Tổng hợp trực tiếp độ dài thời gian trên một bảng, không ghép lịch sử sự kiện.",
    "primary_skill_group": "S3"
  }
}$ent_020_validation$::jsonb
);

-- ENT-021
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_021_question_id$ENT-021$ent_021_question_id$,
$ent_021_world_id$enterprise_v1$ent_021_world_id$,
$ent_021_title$Đơn giao đến thành phố khác địa chỉ mặc định$ent_021_title$,
$ent_021_question_text$Liệt kê đơn có city của địa chỉ giao khác city của một địa chỉ mặc định hiện có của khách. Chỉ so với địa chỉ mặc định được lưu hiện tại, không suy lịch sử thay đổi địa chỉ.
Cột kết quả theo thứ tự: order_id, customer_id, shipping_city, default_address_id, default_city.
Sắp xếp: order_id tăng, default_address_id tăng.
Quy tắc biên: Không có địa chỉ mặc định thì không xuất hiện; nhiều mặc định thì so từng địa chỉ.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_021_question_text$,
$ent_021_reference_sql$SELECT o.order_id, o.customer_id, a.city AS shipping_city,
       d.address_id AS default_address_id, d.city AS default_city
FROM orders o JOIN customer_addresses a
  ON a.address_id=o.shipping_address_id AND a.customer_id=o.customer_id
JOIN customer_addresses d ON d.customer_id=o.customer_id AND d.is_default
WHERE a.city<>d.city ORDER BY o.order_id, d.address_id;$ent_021_reference_sql$,
$ent_021_difficulty$medium$ent_021_difficulty$,
$ent_021_primary_skill_group$S2$ent_021_primary_skill_group$,
$ent_021_primary_business_domain$Customer Management$ent_021_primary_business_domain$,
$ent_021_skills$[]$ent_021_skills$::jsonb,
NULL,
$ent_021_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê đơn có city của địa chỉ giao khác city của một địa chỉ mặc định hiện có của khách. Chỉ so với địa chỉ mặc định được lưu hiện tại, không suy lịch sử thay đổi địa chỉ.",
  "output_grain": "Một đơn và địa chỉ mặc định được so sánh",
  "tables_used": [
    "orders",
    "customer_addresses"
  ],
  "difficulty_reason": "Phân biệt hai vai trò địa chỉ, nối đúng chủ sở hữu rồi so sánh city; không chỉ tra tên.",
  "order_by": "order_id tăng, default_address_id tăng",
  "edge_cases": "Không có địa chỉ mặc định thì không xuất hiện; nhiều mặc định thì so từng địa chỉ.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Đơn giao đến thành phố khác địa chỉ mặc định",
    "central_table": "orders",
    "grain": "Một đơn và địa chỉ mặc định được so sánh",
    "transformation": "two address roles composite owner join city comparison",
    "predicate": "Liệt kê đơn có city của địa chỉ giao khác city của một địa chỉ mặc định hiện có của khách. Chỉ so với địa chỉ mặc định được lưu hiện tại, không suy lịch sử thay đổi địa chỉ.",
    "edge_cases": "Không có địa chỉ mặc định thì không xuất hiện; nhiều mặc định thì so từng địa chỉ."
  },
  "output_columns": [
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "customer_id",
      "meaning": "Mã khách hàng"
    },
    {
      "name": "shipping_city",
      "meaning": "Thành phố địa chỉ giao hàng của đơn"
    },
    {
      "name": "default_address_id",
      "meaning": "Mã địa chỉ mặc định được so sánh"
    },
    {
      "name": "default_city",
      "meaning": "Thành phố địa chỉ mặc định"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_021_metadata$::jsonb,
$ent_021_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 99,
  "runtime_ms": 9.948,
  "column_types": [
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "customer_id",
      "postgres_type": "integer"
    },
    {
      "name": "shipping_city",
      "postgres_type": "character varying(100)"
    },
    {
      "name": "default_address_id",
      "postgres_type": "integer"
    },
    {
      "name": "default_city",
      "postgres_type": "character varying(100)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "order_id": 31,
        "customer_id": 175,
        "default_city": "Hai Phong",
        "shipping_city": "Quy Nhon",
        "default_address_id": 211
      },
      {
        "order_id": 36,
        "customer_id": 205,
        "default_city": "Da Nang",
        "shipping_city": "Can Tho",
        "default_address_id": 247
      },
      {
        "order_id": 57,
        "customer_id": 165,
        "default_city": "Ha Noi",
        "shipping_city": "Can Tho",
        "default_address_id": 198
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "customer_addresses",
    "orders"
  ],
  "process_wall_ms": 81.289,
  "oracle_row_count": 99,
  "result_sha256": "4f7c74f7e56fce1486a026ad54f4a3364ec62717a8af27ac08ed3dba6a05fcf6",
  "oracle_sha256": "4f7c74f7e56fce1486a026ad54f4a3364ec62717a8af27ac08ed3dba6a05fcf6",
  "repeat_runtime_ms": 9.805,
  "repeat_result_sha256": "4f7c74f7e56fce1486a026ad54f4a3364ec62717a8af27ac08ed3dba6a05fcf6",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Phân biệt hai vai trò địa chỉ, nối đúng chủ sở hữu rồi so sánh city; không chỉ tra tên.",
    "primary_skill_group": "S2"
  }
}$ent_021_validation$::jsonb
);

-- ENT-022
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_022_question_id$ENT-022$ent_022_question_id$,
$ent_022_world_id$enterprise_v1$ent_022_world_id$,
$ent_022_title$Tiến độ xuất từng dòng đơn đang xử lý$ent_022_title$,
$ent_022_question_text$Liệt kê từng dòng của đơn status='processing', kho của đơn và tên kho nếu có; nối giao dịch sale bằng order_item_id để cho biết đã xuất hay chưa và thời điểm xuất.
Cột kết quả theo thứ tự: order_id, order_item_id, product_id, quantity, warehouse_id, warehouse_name, has_sale, sale_at.
Sắp xếp: order_id tăng, order_item_id tăng.
Quy tắc biên: Kho hoặc sale có thể NULL; has_sale=false khi chưa xuất.
Thời gian: sale_at là transaction_date của sale.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_022_question_text$,
$ent_022_reference_sql$SELECT o.order_id, i.order_item_id, i.product_id, i.quantity, o.warehouse_id,
       w.warehouse_name, t.transaction_id IS NOT NULL AS has_sale, t.transaction_date AS sale_at
FROM orders o JOIN order_items i ON i.order_id=o.order_id
LEFT JOIN warehouses w ON w.warehouse_id=o.warehouse_id
LEFT JOIN inventory_transactions t ON t.order_item_id=i.order_item_id AND t.transaction_type='sale'
WHERE o.status='processing' ORDER BY o.order_id, i.order_item_id;$ent_022_reference_sql$,
$ent_022_difficulty$medium$ent_022_difficulty$,
$ent_022_primary_skill_group$S2$ent_022_primary_skill_group$,
$ent_022_primary_business_domain$Sales & Orders$ent_022_primary_business_domain$,
$ent_022_skills$[]$ent_022_skills$::jsonb,
NULL,
$ent_022_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê từng dòng của đơn status='processing', kho của đơn và tên kho nếu có; nối giao dịch sale bằng order_item_id để cho biết đã xuất hay chưa và thời điểm xuất.",
  "output_grain": "Một dòng hàng của đơn processing",
  "tables_used": [
    "orders",
    "order_items",
    "warehouses",
    "inventory_transactions"
  ],
  "difficulty_reason": "Phối hợp dòng hàng, kho tùy chọn và liên kết sale có điều kiện, vẫn giữ dòng chưa xuất.",
  "order_by": "order_id tăng, order_item_id tăng",
  "edge_cases": "Kho hoặc sale có thể NULL; has_sale=false khi chưa xuất.",
  "time_basis": "sale_at là transaction_date của sale.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Tiến độ xuất từng dòng đơn đang xử lý",
    "central_table": "orders",
    "grain": "Một dòng hàng của đơn processing",
    "transformation": "processing line optional warehouse and conditional sale join",
    "predicate": "Liệt kê từng dòng của đơn status='processing', kho của đơn và tên kho nếu có; nối giao dịch sale bằng order_item_id để cho biết đã xuất hay chưa và thời điểm xuất.",
    "edge_cases": "Kho hoặc sale có thể NULL; has_sale=false khi chưa xuất."
  },
  "output_columns": [
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "order_item_id",
      "meaning": "Mã dòng hàng"
    },
    {
      "name": "product_id",
      "meaning": "Mã sản phẩm"
    },
    {
      "name": "quantity",
      "meaning": "Số đơn vị trên dòng hàng"
    },
    {
      "name": "warehouse_id",
      "meaning": "Mã kho"
    },
    {
      "name": "warehouse_name",
      "meaning": "Tên kho"
    },
    {
      "name": "has_sale",
      "meaning": "Có sale liên kết dòng hàng hay không"
    },
    {
      "name": "sale_at",
      "meaning": "Thời điểm transaction_date của sale, có thể NULL"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_022_metadata$::jsonb,
$ent_022_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 467,
  "runtime_ms": 16.424,
  "column_types": [
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "order_item_id",
      "postgres_type": "integer"
    },
    {
      "name": "product_id",
      "postgres_type": "integer"
    },
    {
      "name": "quantity",
      "postgres_type": "integer"
    },
    {
      "name": "warehouse_id",
      "postgres_type": "integer"
    },
    {
      "name": "warehouse_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "has_sale",
      "postgres_type": "boolean"
    },
    {
      "name": "sale_at",
      "postgres_type": "timestamp without time zone"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "sale_at": null,
        "has_sale": false,
        "order_id": 12,
        "quantity": 2,
        "product_id": 85,
        "warehouse_id": 2,
        "order_item_id": 27,
        "warehouse_name": "Warehouse Ho Chi Minh"
      },
      {
        "sale_at": null,
        "has_sale": false,
        "order_id": 12,
        "quantity": 1,
        "product_id": 30,
        "warehouse_id": 2,
        "order_item_id": 28,
        "warehouse_name": "Warehouse Ho Chi Minh"
      },
      {
        "sale_at": null,
        "has_sale": false,
        "order_id": 12,
        "quantity": 4,
        "product_id": 172,
        "warehouse_id": 2,
        "order_item_id": 29,
        "warehouse_name": "Warehouse Ho Chi Minh"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "inventory_transactions",
    "order_items",
    "orders",
    "warehouses"
  ],
  "process_wall_ms": 88.302,
  "oracle_row_count": 467,
  "result_sha256": "c81ffd68b796490f9fa596ccdd618d5a3f434ac96c72e040ea1d89fb95182a2f",
  "oracle_sha256": "c81ffd68b796490f9fa596ccdd618d5a3f434ac96c72e040ea1d89fb95182a2f",
  "repeat_runtime_ms": 17.691,
  "repeat_result_sha256": "c81ffd68b796490f9fa596ccdd618d5a3f434ac96c72e040ea1d89fb95182a2f",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Phối hợp dòng hàng, kho tùy chọn và liên kết sale có điều kiện, vẫn giữ dòng chưa xuất.",
    "primary_skill_group": "S2"
  }
}$ent_022_validation$::jsonb
);

-- ENT-023
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_023_question_id$ENT-023$ent_023_question_id$,
$ent_023_world_id$enterprise_v1$ent_023_world_id$,
$ent_023_title$Đối chiếu vai trò quản lý kho và trưởng phòng$ent_023_title$,
$ent_023_question_text$Với mỗi kho, tìm người quản lý kho, phòng của người đó và trưởng phòng được chỉ định. Cho biết người quản lý kho có đồng thời là trưởng phòng đó hay không.
Cột kết quả theo thứ tự: warehouse_id, warehouse_manager_id, warehouse_manager_name, department_name, department_manager_id, same_person.
Sắp xếp: warehouse_id tăng.
Quy tắc biên: same_person=NULL nếu thiếu một trong hai ID, không thay NULL bằng false.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_023_question_text$,
$ent_023_reference_sql$SELECT w.warehouse_id, e.employee_id AS warehouse_manager_id,
       e.full_name AS warehouse_manager_name, d.department_name,
       d.manager_employee_id AS department_manager_id,
       e.employee_id=d.manager_employee_id AS same_person
FROM warehouses w LEFT JOIN employees e ON e.employee_id=w.manager_employee_id
LEFT JOIN departments d ON d.department_id=e.department_id ORDER BY w.warehouse_id;$ent_023_reference_sql$,
$ent_023_difficulty$medium$ent_023_difficulty$,
$ent_023_primary_skill_group$S2$ent_023_primary_skill_group$,
$ent_023_primary_business_domain$Human Resources$ent_023_primary_business_domain$,
$ent_023_skills$[]$ent_023_skills$::jsonb,
NULL,
$ent_023_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Với mỗi kho, tìm người quản lý kho, phòng của người đó và trưởng phòng được chỉ định. Cho biết người quản lý kho có đồng thời là trưởng phòng đó hay không.",
  "output_grain": "Một kho",
  "tables_used": [
    "warehouses",
    "employees",
    "departments"
  ],
  "difficulty_reason": "Nối chuỗi vai trò quản lý và so sánh hai khóa có thể NULL; cần phân biệt quản lý kho với trưởng phòng.",
  "order_by": "warehouse_id tăng",
  "edge_cases": "same_person=NULL nếu thiếu một trong hai ID, không thay NULL bằng false.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Đối chiếu vai trò quản lý kho và trưởng phòng",
    "central_table": "warehouses",
    "grain": "Một kho",
    "transformation": "warehouse manager department designated manager role comparison",
    "predicate": "Với mỗi kho, tìm người quản lý kho, phòng của người đó và trưởng phòng được chỉ định. Cho biết người quản lý kho có đồng thời là trưởng phòng đó hay không.",
    "edge_cases": "same_person=NULL nếu thiếu một trong hai ID, không thay NULL bằng false."
  },
  "output_columns": [
    {
      "name": "warehouse_id",
      "meaning": "Mã kho"
    },
    {
      "name": "warehouse_manager_id",
      "meaning": "Mã người quản lý kho"
    },
    {
      "name": "warehouse_manager_name",
      "meaning": "Tên người quản lý kho"
    },
    {
      "name": "department_name",
      "meaning": "Tên phòng ban"
    },
    {
      "name": "department_manager_id",
      "meaning": "Mã trưởng phòng của người quản lý kho"
    },
    {
      "name": "same_person",
      "meaning": "Hai người giữ vai trò quản lý có trùng ID; NULL nếu thiếu ID"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_023_metadata$::jsonb,
$ent_023_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 6.369,
  "column_types": [
    {
      "name": "warehouse_id",
      "postgres_type": "integer"
    },
    {
      "name": "warehouse_manager_id",
      "postgres_type": "integer"
    },
    {
      "name": "warehouse_manager_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "department_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "department_manager_id",
      "postgres_type": "integer"
    },
    {
      "name": "same_person",
      "postgres_type": "boolean"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "same_person": true,
        "warehouse_id": 1,
        "department_name": "Logistics",
        "warehouse_manager_id": 8,
        "department_manager_id": 8,
        "warehouse_manager_name": "Hoang Chi Employee 008"
      },
      {
        "same_person": true,
        "warehouse_id": 2,
        "department_name": "Logistics",
        "warehouse_manager_id": 8,
        "department_manager_id": 8,
        "warehouse_manager_name": "Hoang Chi Employee 008"
      },
      {
        "same_person": true,
        "warehouse_id": 3,
        "department_name": "Logistics",
        "warehouse_manager_id": 8,
        "department_manager_id": 8,
        "warehouse_manager_name": "Hoang Chi Employee 008"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "departments",
    "employees",
    "warehouses"
  ],
  "process_wall_ms": 77.801,
  "oracle_row_count": 8,
  "result_sha256": "447cbfd775ea012c50e9f5b15fdce6cba6cbb82038f511add1187f7627fde0f9",
  "oracle_sha256": "447cbfd775ea012c50e9f5b15fdce6cba6cbb82038f511add1187f7627fde0f9",
  "repeat_runtime_ms": 6.067,
  "repeat_result_sha256": "447cbfd775ea012c50e9f5b15fdce6cba6cbb82038f511add1187f7627fde0f9",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Nối chuỗi vai trò quản lý và so sánh hai khóa có thể NULL; cần phân biệt quản lý kho với trưởng phòng.",
    "primary_skill_group": "S2"
  }
}$ent_023_validation$::jsonb
);

-- ENT-024
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_024_question_id$ENT-024$ent_024_question_id$,
$ent_024_world_id$enterprise_v1$ent_024_world_id$,
$ent_024_title$Nhân viên xử lý ít nhất năm đơn đã giao$ent_024_title$,
$ent_024_question_text$Theo employee_id được gán trên đơn (loại NULL), đếm toàn bộ đơn, số đơn delivered và tổng total_amount chỉ của đơn delivered. Giữ người có ít nhất 5 đơn delivered.
Cột kết quả theo thứ tự: employee_id, assigned_orders, delivered_orders, delivered_order_value.
Sắp xếp: employee_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_024_question_text$,
$ent_024_reference_sql$SELECT employee_id, COUNT(*) AS assigned_orders,
       COUNT(*) FILTER (WHERE status='delivered') AS delivered_orders,
       SUM(total_amount) FILTER (WHERE status='delivered') AS delivered_order_value
FROM orders WHERE employee_id IS NOT NULL GROUP BY employee_id
HAVING COUNT(*) FILTER (WHERE status='delivered')>=5 ORDER BY employee_id;$ent_024_reference_sql$,
$ent_024_difficulty$medium$ent_024_difficulty$,
$ent_024_primary_skill_group$S3$ent_024_primary_skill_group$,
$ent_024_primary_business_domain$Sales & Orders$ent_024_primary_business_domain$,
$ent_024_skills$[
  "conditional_aggregation"
]$ent_024_skills$::jsonb,
NULL,
$ent_024_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Theo employee_id được gán trên đơn (loại NULL), đếm toàn bộ đơn, số đơn delivered và tổng total_amount chỉ của đơn delivered. Giữ người có ít nhất 5 đơn delivered.",
  "output_grain": "Một nhân viên được gán đơn",
  "tables_used": [
    "orders"
  ],
  "difficulty_reason": "Tổng hợp có điều kiện và lọc nhóm; tránh tính đơn chưa giao vào giá trị đã giao.",
  "order_by": "employee_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Nhân viên xử lý ít nhất năm đơn đã giao",
    "central_table": "orders",
    "grain": "Một nhân viên được gán đơn",
    "transformation": "conditional order aggregates employee having delivered minimum",
    "predicate": "Theo employee_id được gán trên đơn (loại NULL), đếm toàn bộ đơn, số đơn delivered và tổng total_amount chỉ của đơn delivered. Giữ người có ít nhất 5 đơn delivered.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "employee_id",
      "meaning": "Mã nhân viên"
    },
    {
      "name": "assigned_orders",
      "meaning": "Số đơn được gán nhân viên"
    },
    {
      "name": "delivered_orders",
      "meaning": "Số đơn delivered được gán nhân viên"
    },
    {
      "name": "delivered_order_value",
      "meaning": "Tổng total_amount của đơn delivered, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_024_metadata$::jsonb,
$ent_024_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 22,
  "runtime_ms": 5.769,
  "column_types": [
    {
      "name": "employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "assigned_orders",
      "postgres_type": "bigint"
    },
    {
      "name": "delivered_orders",
      "postgres_type": "bigint"
    },
    {
      "name": "delivered_order_value",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "employee_id": 1,
        "assigned_orders": 14,
        "delivered_orders": 6,
        "delivered_order_value": "26239397.61"
      },
      {
        "employee_id": 3,
        "assigned_orders": 12,
        "delivered_orders": 6,
        "delivered_order_value": "19093041.57"
      },
      {
        "employee_id": 8,
        "assigned_orders": 11,
        "delivered_orders": 5,
        "delivered_order_value": "27592540.41"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "orders"
  ],
  "process_wall_ms": 80.508,
  "oracle_row_count": 22,
  "result_sha256": "0679b8b3f2bf6c98f3e643298830872780a97cd2b6edb089c39ec87dce3dcefa",
  "oracle_sha256": "0679b8b3f2bf6c98f3e643298830872780a97cd2b6edb089c39ec87dce3dcefa",
  "repeat_runtime_ms": 4.783,
  "repeat_result_sha256": "0679b8b3f2bf6c98f3e643298830872780a97cd2b6edb089c39ec87dce3dcefa",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Tổng hợp có điều kiện và lọc nhóm; tránh tính đơn chưa giao vào giá trị đã giao.",
    "primary_skill_group": "S3"
  }
}$ent_024_validation$::jsonb
);

-- ENT-025
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_025_question_id$ENT-025$ent_025_question_id$,
$ent_025_world_id$enterprise_v1$ent_025_world_id$,
$ent_025_title$Nhà cung cấp có danh mục hàng hoạt động đa dạng$ent_025_title$,
$ent_025_question_text$Trong sản phẩm is_active=true, theo supplier_id tính số sản phẩm, số category_id khác nhau và trung bình list_price-cost_price. Chỉ giữ nhóm có ít nhất 5 sản phẩm và 3 danh mục.
Cột kết quả theo thứ tự: supplier_id, active_products, category_count, avg_unit_margin.
Sắp xếp: supplier_id tăng.
Quy tắc biên: avg_unit_margin làm tròn 2 chữ số; là chênh giá trên một đơn vị, không phải lợi nhuận thực tế.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_025_question_text$,
$ent_025_reference_sql$SELECT supplier_id, COUNT(*) AS active_products, COUNT(DISTINCT category_id) AS category_count,
       ROUND(AVG(list_price-cost_price),2) AS avg_unit_margin
FROM products WHERE is_active GROUP BY supplier_id
HAVING COUNT(*)>=5 AND COUNT(DISTINCT category_id)>=3 ORDER BY supplier_id;$ent_025_reference_sql$,
$ent_025_difficulty$medium$ent_025_difficulty$,
$ent_025_primary_skill_group$S3$ent_025_primary_skill_group$,
$ent_025_primary_business_domain$Product & Inventory$ent_025_primary_business_domain$,
$ent_025_skills$[]$ent_025_skills$::jsonb,
NULL,
$ent_025_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Trong sản phẩm is_active=true, theo supplier_id tính số sản phẩm, số category_id khác nhau và trung bình list_price-cost_price. Chỉ giữ nhóm có ít nhất 5 sản phẩm và 3 danh mục.",
  "output_grain": "Một nhà cung cấp đạt điều kiện",
  "tables_used": [
    "products"
  ],
  "difficulty_reason": "Kết hợp lọc dòng, nhiều phép tổng hợp và hai điều kiện HAVING.",
  "order_by": "supplier_id tăng",
  "edge_cases": "avg_unit_margin làm tròn 2 chữ số; là chênh giá trên một đơn vị, không phải lợi nhuận thực tế.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Nhà cung cấp có danh mục hàng hoạt động đa dạng",
    "central_table": "products",
    "grain": "Một nhà cung cấp đạt điều kiện",
    "transformation": "supplier active assortment distinct category having average margin",
    "predicate": "Trong sản phẩm is_active=true, theo supplier_id tính số sản phẩm, số category_id khác nhau và trung bình list_price-cost_price. Chỉ giữ nhóm có ít nhất 5 sản phẩm và 3 danh mục.",
    "edge_cases": "avg_unit_margin làm tròn 2 chữ số; là chênh giá trên một đơn vị, không phải lợi nhuận thực tế."
  },
  "output_columns": [
    {
      "name": "supplier_id",
      "meaning": "Mã nhà cung cấp"
    },
    {
      "name": "active_products",
      "meaning": "Số sản phẩm đang hoạt động"
    },
    {
      "name": "category_count",
      "meaning": "Số danh mục trực tiếp khác nhau"
    },
    {
      "name": "avg_unit_margin",
      "meaning": "Bình quân list_price-cost_price, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_025_metadata$::jsonb,
$ent_025_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 25,
  "runtime_ms": 4.278,
  "column_types": [
    {
      "name": "supplier_id",
      "postgres_type": "integer"
    },
    {
      "name": "active_products",
      "postgres_type": "bigint"
    },
    {
      "name": "category_count",
      "postgres_type": "bigint"
    },
    {
      "name": "avg_unit_margin",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "supplier_id": 1,
        "category_count": 5,
        "active_products": 7,
        "avg_unit_margin": "128223.86"
      },
      {
        "supplier_id": 2,
        "category_count": 5,
        "active_products": 7,
        "avg_unit_margin": "184315.52"
      },
      {
        "supplier_id": 3,
        "category_count": 7,
        "active_products": 9,
        "avg_unit_margin": "139840.18"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "products"
  ],
  "process_wall_ms": 75.342,
  "oracle_row_count": 25,
  "result_sha256": "b0beff83d7224005e4d736d63b80583fceb51acd9b4fdc2828255a5b8d2904ea",
  "oracle_sha256": "b0beff83d7224005e4d736d63b80583fceb51acd9b4fdc2828255a5b8d2904ea",
  "repeat_runtime_ms": 5.547,
  "repeat_result_sha256": "b0beff83d7224005e4d736d63b80583fceb51acd9b4fdc2828255a5b8d2904ea",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Kết hợp lọc dòng, nhiều phép tổng hợp và hai điều kiện HAVING.",
    "primary_skill_group": "S3"
  }
}$ent_025_validation$::jsonb
);

-- ENT-026
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_026_question_id$ENT-026$ent_026_question_id$,
$ent_026_world_id$enterprise_v1$ent_026_world_id$,
$ent_026_title$Khách có địa chỉ tại nhiều thành phố$ent_026_title$,
$ent_026_question_text$Theo customer_id trong customer_addresses, đếm địa chỉ, số city khác nhau và số địa chỉ mặc định. Chỉ giữ khách có ít nhất 2 city.
Cột kết quả theo thứ tự: customer_id, address_count, city_count, default_count.
Sắp xếp: customer_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_026_question_text$,
$ent_026_reference_sql$SELECT customer_id, COUNT(*) AS address_count, COUNT(DISTINCT city) AS city_count,
       COUNT(*) FILTER (WHERE is_default) AS default_count
FROM customer_addresses GROUP BY customer_id HAVING COUNT(DISTINCT city)>=2 ORDER BY customer_id;$ent_026_reference_sql$,
$ent_026_difficulty$medium$ent_026_difficulty$,
$ent_026_primary_skill_group$S3$ent_026_primary_skill_group$,
$ent_026_primary_business_domain$Customer Management$ent_026_primary_business_domain$,
$ent_026_skills$[
  "conditional_aggregation"
]$ent_026_skills$::jsonb,
NULL,
$ent_026_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Theo customer_id trong customer_addresses, đếm địa chỉ, số city khác nhau và số địa chỉ mặc định. Chỉ giữ khách có ít nhất 2 city.",
  "output_grain": "Một khách đa thành phố",
  "tables_used": [
    "customer_addresses"
  ],
  "difficulty_reason": "Cần COUNT DISTINCT, tổng hợp có điều kiện và lọc nhóm.",
  "order_by": "customer_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Khách có địa chỉ tại nhiều thành phố",
    "central_table": "customer_addresses",
    "grain": "Một khách đa thành phố",
    "transformation": "customer address diversity distinct count having",
    "predicate": "Theo customer_id trong customer_addresses, đếm địa chỉ, số city khác nhau và số địa chỉ mặc định. Chỉ giữ khách có ít nhất 2 city.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "customer_id",
      "meaning": "Mã khách hàng"
    },
    {
      "name": "address_count",
      "meaning": "Số địa chỉ của khách"
    },
    {
      "name": "city_count",
      "meaning": "Số thành phố khác nhau của khách"
    },
    {
      "name": "default_count",
      "meaning": "Số địa chỉ được đánh dấu mặc định"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_026_metadata$::jsonb,
$ent_026_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 53,
  "runtime_ms": 4.502,
  "column_types": [
    {
      "name": "customer_id",
      "postgres_type": "integer"
    },
    {
      "name": "address_count",
      "postgres_type": "bigint"
    },
    {
      "name": "city_count",
      "postgres_type": "bigint"
    },
    {
      "name": "default_count",
      "postgres_type": "bigint"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "city_count": 2,
        "customer_id": 5,
        "address_count": 2,
        "default_count": 1
      },
      {
        "city_count": 2,
        "customer_id": 10,
        "address_count": 2,
        "default_count": 1
      },
      {
        "city_count": 2,
        "customer_id": 15,
        "address_count": 2,
        "default_count": 1
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "customer_addresses"
  ],
  "process_wall_ms": 174.743,
  "oracle_row_count": 53,
  "result_sha256": "9a0b1ecdad18e6e5d95a3bf338bf6a713c4e2f01cc9333977978ebd90d00ae07",
  "oracle_sha256": "9a0b1ecdad18e6e5d95a3bf338bf6a713c4e2f01cc9333977978ebd90d00ae07",
  "repeat_runtime_ms": 5.209,
  "repeat_result_sha256": "9a0b1ecdad18e6e5d95a3bf338bf6a713c4e2f01cc9333977978ebd90d00ae07",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần COUNT DISTINCT, tổng hợp có điều kiện và lọc nhóm.",
    "primary_skill_group": "S3"
  }
}$ent_026_validation$::jsonb
);

-- ENT-027
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_027_question_id$ENT-027$ent_027_question_id$,
$ent_027_world_id$enterprise_v1$ent_027_world_id$,
$ent_027_title$Chi phí tháng theo phòng và tình trạng phê duyệt$ent_027_title$,
$ent_027_question_text$Theo tháng expense_date và department_id, tính số khoản chi, tổng amount và tổng amount có approved_by_employee_id không NULL. Chỉ giữ nhóm có ít nhất 2 khoản.
Cột kết quả theo thứ tự: month, department_id, expense_count, total_expense, approved_expense.
Sắp xếp: month tăng, department_id tăng NULLS LAST.
Quy tắc biên: Nhóm department_id NULL được giữ; không có chi được phê duyệt thì approved_expense=0.
Thời gian: expense_date; month là ngày đầu tháng.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_027_question_text$,
$ent_027_reference_sql$SELECT DATE_TRUNC('month',expense_date)::date AS month, department_id,
       COUNT(*) AS expense_count, SUM(amount) AS total_expense,
       COALESCE(SUM(amount) FILTER (WHERE approved_by_employee_id IS NOT NULL),0) AS approved_expense
FROM operating_expenses GROUP BY DATE_TRUNC('month',expense_date)::date, department_id
HAVING COUNT(*)>=2 ORDER BY month, department_id NULLS LAST;$ent_027_reference_sql$,
$ent_027_difficulty$medium$ent_027_difficulty$,
$ent_027_primary_skill_group$S3$ent_027_primary_skill_group$,
$ent_027_primary_business_domain$Finance$ent_027_primary_business_domain$,
$ent_027_skills$[
  "conditional_aggregation"
]$ent_027_skills$::jsonb,
NULL,
$ent_027_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Theo tháng expense_date và department_id, tính số khoản chi, tổng amount và tổng amount có approved_by_employee_id không NULL. Chỉ giữ nhóm có ít nhất 2 khoản.",
  "output_grain": "Một tháng và phòng; NULL là nhóm chưa gán phòng",
  "tables_used": [
    "operating_expenses"
  ],
  "difficulty_reason": "Nhóm theo thời gian và phòng, tách chi có người phê duyệt rồi lọc nhóm.",
  "order_by": "month tăng, department_id tăng NULLS LAST",
  "edge_cases": "Nhóm department_id NULL được giữ; không có chi được phê duyệt thì approved_expense=0.",
  "time_basis": "expense_date; month là ngày đầu tháng.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Chi phí tháng theo phòng và tình trạng phê duyệt",
    "central_table": "operating_expenses",
    "grain": "Một tháng và phòng; NULL là nhóm chưa gán phòng",
    "transformation": "monthly department conditional expense sums having",
    "predicate": "Theo tháng expense_date và department_id, tính số khoản chi, tổng amount và tổng amount có approved_by_employee_id không NULL. Chỉ giữ nhóm có ít nhất 2 khoản.",
    "edge_cases": "Nhóm department_id NULL được giữ; không có chi được phê duyệt thì approved_expense=0."
  },
  "output_columns": [
    {
      "name": "month",
      "meaning": "Ngày đầu tháng"
    },
    {
      "name": "department_id",
      "meaning": "Mã phòng hiện tại"
    },
    {
      "name": "expense_count",
      "meaning": "Số khoản chi trong nhóm"
    },
    {
      "name": "total_expense",
      "meaning": "Tổng amount của nhóm chi, VND"
    },
    {
      "name": "approved_expense",
      "meaning": "Tổng chi có người phê duyệt, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_027_metadata$::jsonb,
$ent_027_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 45,
  "runtime_ms": 4.248,
  "column_types": [
    {
      "name": "month",
      "postgres_type": "date"
    },
    {
      "name": "department_id",
      "postgres_type": "integer"
    },
    {
      "name": "expense_count",
      "postgres_type": "bigint"
    },
    {
      "name": "total_expense",
      "postgres_type": "numeric"
    },
    {
      "name": "approved_expense",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "month": "2022-06-01",
        "department_id": 1,
        "expense_count": 3,
        "total_expense": "12479000.00",
        "approved_expense": "12479000.00"
      },
      {
        "month": "2022-06-01",
        "department_id": 5,
        "expense_count": 2,
        "total_expense": "2199000.00",
        "approved_expense": "2199000.00"
      },
      {
        "month": "2022-07-01",
        "department_id": 3,
        "expense_count": 2,
        "total_expense": "4613000.00",
        "approved_expense": "4613000.00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "operating_expenses"
  ],
  "process_wall_ms": 75.281,
  "oracle_row_count": 45,
  "result_sha256": "41646c33f06b29b1f6abd7adadfd59a81bcaa04a8e3614ee75f99e54a84e744d",
  "oracle_sha256": "41646c33f06b29b1f6abd7adadfd59a81bcaa04a8e3614ee75f99e54a84e744d",
  "repeat_runtime_ms": 5.089,
  "repeat_result_sha256": "41646c33f06b29b1f6abd7adadfd59a81bcaa04a8e3614ee75f99e54a84e744d",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Nhóm theo thời gian và phòng, tách chi có người phê duyệt rồi lọc nhóm.",
    "primary_skill_group": "S3"
  }
}$ent_027_validation$::jsonb
);

-- ENT-028
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_028_question_id$ENT-028$ent_028_question_id$,
$ent_028_world_id$enterprise_v1$ent_028_world_id$,
$ent_028_title$Sức chứa còn lại của từng kho$ent_028_title$,
$ent_028_question_text$Với mọi kho, tính tồn hiện tại từ tổng quantity_change của mọi sản phẩm, sức chứa còn lại và phần trăm sử dụng capacity. Bao gồm kho không có giao dịch.
Cột kết quả theo thứ tự: warehouse_id, capacity, current_units, free_capacity, utilization_pct.
Sắp xếp: warehouse_id tăng.
Quy tắc biên: Không có giao dịch thì current_units=0; capacity=0 thì utilization_pct=NULL; phần trăm làm tròn 2 chữ số.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_028_question_text$,
$ent_028_reference_sql$SELECT w.warehouse_id, w.capacity, COALESCE(SUM(t.quantity_change),0) AS current_units,
       w.capacity-COALESCE(SUM(t.quantity_change),0) AS free_capacity,
       ROUND(100.0*COALESCE(SUM(t.quantity_change),0)/NULLIF(w.capacity,0),2) AS utilization_pct
FROM warehouses w LEFT JOIN inventory_transactions t ON t.warehouse_id=w.warehouse_id
GROUP BY w.warehouse_id, w.capacity ORDER BY w.warehouse_id;$ent_028_reference_sql$,
$ent_028_difficulty$medium$ent_028_difficulty$,
$ent_028_primary_skill_group$S3$ent_028_primary_skill_group$,
$ent_028_primary_business_domain$Product & Inventory$ent_028_primary_business_domain$,
$ent_028_skills$[]$ent_028_skills$::jsonb,
NULL,
$ent_028_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Với mọi kho, tính tồn hiện tại từ tổng quantity_change của mọi sản phẩm, sức chứa còn lại và phần trăm sử dụng capacity. Bao gồm kho không có giao dịch.",
  "output_grain": "Một kho",
  "tables_used": [
    "warehouses",
    "inventory_transactions"
  ],
  "difficulty_reason": "Tổng hợp quan hệ một-nhiều và xử lý kho không có giao dịch hoặc capacity=0.",
  "order_by": "warehouse_id tăng",
  "edge_cases": "Không có giao dịch thì current_units=0; capacity=0 thì utilization_pct=NULL; phần trăm làm tròn 2 chữ số.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Sức chứa còn lại của từng kho",
    "central_table": "warehouses",
    "grain": "Một kho",
    "transformation": "warehouse left aggregate current stock capacity ratio",
    "predicate": "Với mọi kho, tính tồn hiện tại từ tổng quantity_change của mọi sản phẩm, sức chứa còn lại và phần trăm sử dụng capacity. Bao gồm kho không có giao dịch.",
    "edge_cases": "Không có giao dịch thì current_units=0; capacity=0 thì utilization_pct=NULL; phần trăm làm tròn 2 chữ số."
  },
  "output_columns": [
    {
      "name": "warehouse_id",
      "meaning": "Mã kho"
    },
    {
      "name": "capacity",
      "meaning": "Sức chứa kho bằng đơn vị sản phẩm"
    },
    {
      "name": "current_units",
      "meaning": "Số đơn vị tồn từ tổng biến động"
    },
    {
      "name": "free_capacity",
      "meaning": "capacity trừ tồn hiện tại"
    },
    {
      "name": "utilization_pct",
      "meaning": "Phần trăm sức chứa đang dùng"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_028_metadata$::jsonb,
$ent_028_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 7.074,
  "column_types": [
    {
      "name": "warehouse_id",
      "postgres_type": "integer"
    },
    {
      "name": "capacity",
      "postgres_type": "integer"
    },
    {
      "name": "current_units",
      "postgres_type": "bigint"
    },
    {
      "name": "free_capacity",
      "postgres_type": "bigint"
    },
    {
      "name": "utilization_pct",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "capacity": 250000,
        "warehouse_id": 1,
        "current_units": 11143,
        "free_capacity": 238857,
        "utilization_pct": "4.46"
      },
      {
        "capacity": 250000,
        "warehouse_id": 2,
        "current_units": 11666,
        "free_capacity": 238334,
        "utilization_pct": "4.67"
      },
      {
        "capacity": 250000,
        "warehouse_id": 3,
        "current_units": 9803,
        "free_capacity": 240197,
        "utilization_pct": "3.92"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "inventory_transactions",
    "warehouses"
  ],
  "process_wall_ms": 77.79,
  "oracle_row_count": 8,
  "result_sha256": "53bf480012a21f2151ac4e0e8bbbc12899bd998f8b0522f3503c1d9de1868573",
  "oracle_sha256": "53bf480012a21f2151ac4e0e8bbbc12899bd998f8b0522f3503c1d9de1868573",
  "repeat_runtime_ms": 7.125,
  "repeat_result_sha256": "53bf480012a21f2151ac4e0e8bbbc12899bd998f8b0522f3503c1d9de1868573",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Tổng hợp quan hệ một-nhiều và xử lý kho không có giao dịch hoặc capacity=0.",
    "primary_skill_group": "S3"
  }
}$ent_028_validation$::jsonb
);

-- ENT-029
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_029_question_id$ENT-029$ent_029_question_id$,
$ent_029_world_id$enterprise_v1$ent_029_world_id$,
$ent_029_title$Khách hàng chưa từng đặt đơn$ent_029_title$,
$ent_029_question_text$Tìm khách hàng không có bất kỳ bản ghi orders nào, không giới hạn status của khách hoặc đơn.
Cột kết quả theo thứ tự: customer_id, full_name, registered_at.
Sắp xếp: customer_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_029_question_text$,
$ent_029_reference_sql$SELECT c.customer_id, c.full_name, c.registered_at FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id) ORDER BY c.customer_id;$ent_029_reference_sql$,
$ent_029_difficulty$medium$ent_029_difficulty$,
$ent_029_primary_skill_group$S4$ent_029_primary_skill_group$,
$ent_029_primary_business_domain$Customer Management$ent_029_primary_business_domain$,
$ent_029_skills$[
  "anti_existence"
]$ent_029_skills$::jsonb,
NULL,
$ent_029_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Tìm khách hàng không có bất kỳ bản ghi orders nào, không giới hạn status của khách hoặc đơn.",
  "output_grain": "Một khách hàng",
  "tables_used": [
    "customers",
    "orders"
  ],
  "difficulty_reason": "Cần xét sự không tồn tại của quan hệ đơn hàng, không chỉ lọc trạng thái khách.",
  "order_by": "customer_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Khách hàng chưa từng đặt đơn",
    "central_table": "customers",
    "grain": "Một khách hàng",
    "transformation": "customer anti existence any order",
    "predicate": "Tìm khách hàng không có bất kỳ bản ghi orders nào, không giới hạn status của khách hoặc đơn.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "customer_id",
      "meaning": "Mã khách hàng"
    },
    {
      "name": "full_name",
      "meaning": "Họ tên được lưu"
    },
    {
      "name": "registered_at",
      "meaning": "Thời điểm đăng ký"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_029_metadata$::jsonb,
$ent_029_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 37,
  "runtime_ms": 6.827,
  "column_types": [
    {
      "name": "customer_id",
      "postgres_type": "integer"
    },
    {
      "name": "full_name",
      "postgres_type": "character varying(150)"
    },
    {
      "name": "registered_at",
      "postgres_type": "timestamp without time zone"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "full_name": "Pham Hung Customer 038",
        "customer_id": 38,
        "registered_at": "2024-11-26T12:00:00"
      },
      {
        "full_name": "Bui Nam Customer 063",
        "customer_id": 63,
        "registered_at": "2025-08-17T11:00:00"
      },
      {
        "full_name": "Le Binh Customer 085",
        "customer_id": 85,
        "registered_at": "2025-05-08T16:15:00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "customers",
    "orders"
  ],
  "process_wall_ms": 78.774,
  "oracle_row_count": 37,
  "result_sha256": "66d1a383d20aea59b281e05f96a0f7d99b1b4fc57d012644b5a973d1dffa9455",
  "oracle_sha256": "66d1a383d20aea59b281e05f96a0f7d99b1b4fc57d012644b5a973d1dffa9455",
  "repeat_runtime_ms": 7.257,
  "repeat_result_sha256": "66d1a383d20aea59b281e05f96a0f7d99b1b4fc57d012644b5a973d1dffa9455",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần xét sự không tồn tại của quan hệ đơn hàng, không chỉ lọc trạng thái khách.",
    "primary_skill_group": "S4"
  }
}$ent_029_validation$::jsonb
);

-- ENT-030
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_030_question_id$ENT-030$ent_030_question_id$,
$ent_030_world_id$enterprise_v1$ent_030_world_id$,
$ent_030_title$Hàng chưa được đặt nhưng vẫn có tồn$ent_030_title$,
$ent_030_question_text$Tìm sản phẩm không xuất hiện trong bất kỳ order_items nào nhưng có ít nhất một kho với SUM(quantity_change)>0.
Cột kết quả theo thứ tự: product_id, product_name.
Sắp xếp: product_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_030_question_text$,
$ent_030_reference_sql$SELECT p.product_id, p.product_name FROM products p
WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.product_id=p.product_id)
  AND EXISTS (SELECT 1 FROM inventory_transactions t WHERE t.product_id=p.product_id
              GROUP BY t.warehouse_id HAVING SUM(t.quantity_change)>0) ORDER BY p.product_id;$ent_030_reference_sql$,
$ent_030_difficulty$medium$ent_030_difficulty$,
$ent_030_primary_skill_group$S4$ent_030_primary_skill_group$,
$ent_030_primary_business_domain$Product & Inventory$ent_030_primary_business_domain$,
$ent_030_skills$[
  "anti_existence"
]$ent_030_skills$::jsonb,
NULL,
$ent_030_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Tìm sản phẩm không xuất hiện trong bất kỳ order_items nào nhưng có ít nhất một kho với SUM(quantity_change)>0.",
  "output_grain": "Một sản phẩm",
  "tables_used": [
    "products",
    "order_items",
    "inventory_transactions"
  ],
  "difficulty_reason": "Kết hợp không tồn tại dòng hàng và tồn tại một nhóm tồn dương.",
  "order_by": "product_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Hàng chưa được đặt nhưng vẫn có tồn",
    "central_table": "products",
    "grain": "Một sản phẩm",
    "transformation": "product anti order existence positive warehouse balance existence",
    "predicate": "Tìm sản phẩm không xuất hiện trong bất kỳ order_items nào nhưng có ít nhất một kho với SUM(quantity_change)>0.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "product_id",
      "meaning": "Mã sản phẩm"
    },
    {
      "name": "product_name",
      "meaning": "Tên sản phẩm"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_030_metadata$::jsonb,
$ent_030_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 11,
  "runtime_ms": 10.728,
  "column_types": [
    {
      "name": "product_id",
      "postgres_type": "integer"
    },
    {
      "name": "product_name",
      "postgres_type": "character varying(200)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "product_id": 231,
        "product_name": "Product 231"
      },
      {
        "product_id": 232,
        "product_name": "Product 232"
      },
      {
        "product_id": 233,
        "product_name": "Product 233"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "inventory_transactions",
    "order_items",
    "products"
  ],
  "process_wall_ms": 190.615,
  "oracle_row_count": 11,
  "result_sha256": "e21f49994d72b0e134ace935023239bc18103de1642e5583ce2ec67c21b46015",
  "oracle_sha256": "e21f49994d72b0e134ace935023239bc18103de1642e5583ce2ec67c21b46015",
  "repeat_runtime_ms": 12.048,
  "repeat_result_sha256": "e21f49994d72b0e134ace935023239bc18103de1642e5583ce2ec67c21b46015",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Kết hợp không tồn tại dòng hàng và tồn tại một nhóm tồn dương.",
    "primary_skill_group": "S4"
  }
}$ent_030_validation$::jsonb
);

-- ENT-031
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_031_question_id$ENT-031$ent_031_question_id$,
$ent_031_world_id$enterprise_v1$ent_031_world_id$,
$ent_031_title$Lương cao hơn trung bình phòng$ent_031_title$,
$ent_031_question_text$Tìm nhân viên có current_salary cao hơn trung bình current_salary của mọi nhân viên cùng department_id, gồm cả bản thân và không lọc status.
Cột kết quả theo thứ tự: employee_id, department_id, current_salary.
Sắp xếp: employee_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_031_question_text$,
$ent_031_reference_sql$SELECT e.employee_id, e.department_id, e.current_salary FROM employees e
WHERE e.current_salary>(SELECT AVG(p.current_salary) FROM employees p WHERE p.department_id=e.department_id)
ORDER BY e.employee_id;$ent_031_reference_sql$,
$ent_031_difficulty$medium$ent_031_difficulty$,
$ent_031_primary_skill_group$S4$ent_031_primary_skill_group$,
$ent_031_primary_business_domain$Human Resources$ent_031_primary_business_domain$,
$ent_031_skills$[]$ent_031_skills$::jsonb,
NULL,
$ent_031_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Tìm nhân viên có current_salary cao hơn trung bình current_salary của mọi nhân viên cùng department_id, gồm cả bản thân và không lọc status.",
  "output_grain": "Một nhân viên",
  "tables_used": [
    "employees"
  ],
  "difficulty_reason": "So sánh từng nhân viên với tổng hợp tương quan theo phòng.",
  "order_by": "employee_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Lương cao hơn trung bình phòng",
    "central_table": "employees",
    "grain": "Một nhân viên",
    "transformation": "correlated department salary average comparison",
    "predicate": "Tìm nhân viên có current_salary cao hơn trung bình current_salary của mọi nhân viên cùng department_id, gồm cả bản thân và không lọc status.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "employee_id",
      "meaning": "Mã nhân viên"
    },
    {
      "name": "department_id",
      "meaning": "Mã phòng hiện tại"
    },
    {
      "name": "current_salary",
      "meaning": "Mức lương hiện tại, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_031_metadata$::jsonb,
$ent_031_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 34,
  "runtime_ms": 5.368,
  "column_types": [
    {
      "name": "employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "department_id",
      "postgres_type": "integer"
    },
    {
      "name": "current_salary",
      "postgres_type": "numeric(15,2)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "employee_id": 1,
        "department_id": 1,
        "current_salary": "71000000.00"
      },
      {
        "employee_id": 2,
        "department_id": 2,
        "current_salary": "77000000.00"
      },
      {
        "employee_id": 3,
        "department_id": 3,
        "current_salary": "65000000.00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "employees"
  ],
  "process_wall_ms": 76.648,
  "oracle_row_count": 34,
  "result_sha256": "ed526ebbe31bff81963cf33030a8fcde028b6a3023408852058477e5a8f00530",
  "oracle_sha256": "ed526ebbe31bff81963cf33030a8fcde028b6a3023408852058477e5a8f00530",
  "repeat_runtime_ms": 4.839,
  "repeat_result_sha256": "ed526ebbe31bff81963cf33030a8fcde028b6a3023408852058477e5a8f00530",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "So sánh từng nhân viên với tổng hợp tương quan theo phòng.",
    "primary_skill_group": "S4"
  }
}$ent_031_validation$::jsonb
);

-- ENT-032
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_032_question_id$ENT-032$ent_032_question_id$,
$ent_032_world_id$enterprise_v1$ent_032_world_id$,
$ent_032_title$Đơn thanh toán thành công sau lần thất bại$ent_032_title$,
$ent_032_question_text$Liệt kê mỗi payment success có ít nhất một payment failed của cùng đơn xảy ra trước, theo cặp (attempted_at,payment_id).
Cột kết quả theo thứ tự: order_id, success_payment_id, success_at.
Sắp xếp: order_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: attempted_at; cùng thời điểm phân thứ tự bằng payment_id.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_032_question_text$,
$ent_032_reference_sql$SELECT s.order_id, s.payment_id AS success_payment_id, s.attempted_at AS success_at FROM payments s
WHERE s.payment_status='success' AND EXISTS (
  SELECT 1 FROM payments f WHERE f.order_id=s.order_id AND f.payment_status='failed'
  AND (f.attempted_at,f.payment_id)<(s.attempted_at,s.payment_id)) ORDER BY s.order_id;$ent_032_reference_sql$,
$ent_032_difficulty$medium$ent_032_difficulty$,
$ent_032_primary_skill_group$S4$ent_032_primary_skill_group$,
$ent_032_primary_business_domain$Sales & Orders$ent_032_primary_business_domain$,
$ent_032_skills$[]$ent_032_skills$::jsonb,
NULL,
$ent_032_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Liệt kê mỗi payment success có ít nhất một payment failed của cùng đơn xảy ra trước, theo cặp (attempted_at,payment_id).",
  "output_grain": "Một đơn có success sau failed",
  "tables_used": [
    "payments"
  ],
  "difficulty_reason": "Cần kiểm tra tồn tại sự kiện trước success với khóa thời gian ổn định.",
  "order_by": "order_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "attempted_at; cùng thời điểm phân thứ tự bằng payment_id.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Đơn thanh toán thành công sau lần thất bại",
    "central_table": "payments",
    "grain": "Một đơn có success sau failed",
    "transformation": "success payment correlated earlier failed existence",
    "predicate": "Liệt kê mỗi payment success có ít nhất một payment failed của cùng đơn xảy ra trước, theo cặp (attempted_at,payment_id).",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "success_payment_id",
      "meaning": "Mã payment success được xét"
    },
    {
      "name": "success_at",
      "meaning": "Thời điểm attempted_at của payment success"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_032_metadata$::jsonb,
$ent_032_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 446,
  "runtime_ms": 7.178,
  "column_types": [
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "success_payment_id",
      "postgres_type": "integer"
    },
    {
      "name": "success_at",
      "postgres_type": "timestamp without time zone"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "order_id": 1,
        "success_at": "2026-07-30T10:25:00",
        "success_payment_id": 3
      },
      {
        "order_id": 2,
        "success_at": "2025-10-23T18:45:00",
        "success_payment_id": 5
      },
      {
        "order_id": 3,
        "success_at": "2026-02-12T16:05:00",
        "success_payment_id": 7
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "payments"
  ],
  "process_wall_ms": 79.181,
  "oracle_row_count": 446,
  "result_sha256": "f0082e379fad9dfb20ae2fb0151a52db11ad6692b9cb3451c433fcf1c3c67f1f",
  "oracle_sha256": "f0082e379fad9dfb20ae2fb0151a52db11ad6692b9cb3451c433fcf1c3c67f1f",
  "repeat_runtime_ms": 6.131,
  "repeat_result_sha256": "f0082e379fad9dfb20ae2fb0151a52db11ad6692b9cb3451c433fcf1c3c67f1f",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần kiểm tra tồn tại sự kiện trước success với khóa thời gian ổn định.",
    "primary_skill_group": "S4"
  }
}$ent_032_validation$::jsonb
);

-- ENT-033
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_033_question_id$ENT-033$ent_033_question_id$,
$ent_033_world_id$enterprise_v1$ent_033_world_id$,
$ent_033_title$Nhà cung cấp hoạt động không có hàng ngừng bán$ent_033_title$,
$ent_033_question_text$Tìm supplier status='active' có ít nhất một sản phẩm và không có sản phẩm is_active=false.
Cột kết quả theo thứ tự: supplier_id, supplier_name.
Sắp xếp: supplier_id tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_033_question_text$,
$ent_033_reference_sql$SELECT s.supplier_id, s.supplier_name FROM suppliers s
WHERE s.status='active' AND EXISTS (SELECT 1 FROM products p WHERE p.supplier_id=s.supplier_id)
AND NOT EXISTS (SELECT 1 FROM products p WHERE p.supplier_id=s.supplier_id AND NOT p.is_active)
ORDER BY s.supplier_id;$ent_033_reference_sql$,
$ent_033_difficulty$medium$ent_033_difficulty$,
$ent_033_primary_skill_group$S4$ent_033_primary_skill_group$,
$ent_033_primary_business_domain$Product & Inventory$ent_033_primary_business_domain$,
$ent_033_skills$[
  "anti_existence"
]$ent_033_skills$::jsonb,
NULL,
$ent_033_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Tìm supplier status='active' có ít nhất một sản phẩm và không có sản phẩm is_active=false.",
  "output_grain": "Một nhà cung cấp",
  "tables_used": [
    "suppliers",
    "products"
  ],
  "difficulty_reason": "Kết hợp EXISTS và NOT EXISTS để diễn đạt điều kiện mọi sản phẩm mà không nhận nhóm rỗng.",
  "order_by": "supplier_id tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Nhà cung cấp hoạt động không có hàng ngừng bán",
    "central_table": "suppliers",
    "grain": "Một nhà cung cấp",
    "transformation": "supplier nonvacuous all products active",
    "predicate": "Tìm supplier status='active' có ít nhất một sản phẩm và không có sản phẩm is_active=false.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "supplier_id",
      "meaning": "Mã nhà cung cấp"
    },
    {
      "name": "supplier_name",
      "meaning": "Tên nhà cung cấp"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_033_metadata$::jsonb,
$ent_033_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 17,
  "runtime_ms": 5.434,
  "column_types": [
    {
      "name": "supplier_id",
      "postgres_type": "integer"
    },
    {
      "name": "supplier_name",
      "postgres_type": "character varying(150)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "supplier_id": 1,
        "supplier_name": "Supplier 01"
      },
      {
        "supplier_id": 2,
        "supplier_name": "Supplier 02"
      },
      {
        "supplier_id": 6,
        "supplier_name": "Supplier 06"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "products",
    "suppliers"
  ],
  "process_wall_ms": 77.382,
  "oracle_row_count": 17,
  "result_sha256": "f47b66e79bf318a02499046903eed31bf098f7e1e7c0093d30783fd29be5fb99",
  "oracle_sha256": "f47b66e79bf318a02499046903eed31bf098f7e1e7c0093d30783fd29be5fb99",
  "repeat_runtime_ms": 7.01,
  "repeat_result_sha256": "f47b66e79bf318a02499046903eed31bf098f7e1e7c0093d30783fd29be5fb99",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Kết hợp EXISTS và NOT EXISTS để diễn đạt điều kiện mọi sản phẩm mà không nhận nhóm rỗng.",
    "primary_skill_group": "S4"
  }
}$ent_033_validation$::jsonb
);

-- ENT-034
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_034_question_id$ENT-034$ent_034_question_id$,
$ent_034_world_id$enterprise_v1$ent_034_world_id$,
$ent_034_title$Đơn trả hàng vật lý chưa có hoàn tiền hoàn tất$ent_034_title$,
$ent_034_question_text$Tìm đơn delivered có giao dịch return liên kết ít nhất một dòng hàng, nhưng không có refund completed qua bất kỳ payment của đơn. Đây là danh sách đối soát, không kết luận vi phạm BR.
Cột kết quả theo thứ tự: order_id, customer_id, total_amount.
Sắp xếp: order_id tăng.
Quy tắc biên: Refund pending/failed không loại đơn; không giả định trả hàng vật lý luôn có refund.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_034_question_text$,
$ent_034_reference_sql$SELECT o.order_id, o.customer_id, o.total_amount FROM orders o WHERE o.status='delivered'
AND EXISTS (SELECT 1 FROM order_items i JOIN inventory_transactions t ON t.order_item_id=i.order_item_id
            WHERE i.order_id=o.order_id AND t.transaction_type='return')
AND NOT EXISTS (SELECT 1 FROM payments p JOIN refunds r ON r.payment_id=p.payment_id
                WHERE p.order_id=o.order_id AND r.refund_status='completed') ORDER BY o.order_id;$ent_034_reference_sql$,
$ent_034_difficulty$medium$ent_034_difficulty$,
$ent_034_primary_skill_group$S4$ent_034_primary_skill_group$,
$ent_034_primary_business_domain$Sales & Orders$ent_034_primary_business_domain$,
$ent_034_skills$[
  "anti_existence"
]$ent_034_skills$::jsonb,
NULL,
$ent_034_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Tìm đơn delivered có giao dịch return liên kết ít nhất một dòng hàng, nhưng không có refund completed qua bất kỳ payment của đơn. Đây là danh sách đối soát, không kết luận vi phạm BR.",
  "output_grain": "Một đơn hàng",
  "tables_used": [
    "orders",
    "order_items",
    "inventory_transactions",
    "payments",
    "refunds"
  ],
  "difficulty_reason": "Đối chiếu tồn tại trả hàng vật lý với không tồn tại hoàn tiền qua hai quan hệ khác.",
  "order_by": "order_id tăng",
  "edge_cases": "Refund pending/failed không loại đơn; không giả định trả hàng vật lý luôn có refund.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Đơn trả hàng vật lý chưa có hoàn tiền hoàn tất",
    "central_table": "orders",
    "grain": "Một đơn hàng",
    "transformation": "physical return existence anti completed monetary refund",
    "predicate": "Tìm đơn delivered có giao dịch return liên kết ít nhất một dòng hàng, nhưng không có refund completed qua bất kỳ payment của đơn. Đây là danh sách đối soát, không kết luận vi phạm BR.",
    "edge_cases": "Refund pending/failed không loại đơn; không giả định trả hàng vật lý luôn có refund."
  },
  "output_columns": [
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "customer_id",
      "meaning": "Mã khách hàng"
    },
    {
      "name": "total_amount",
      "meaning": "Giá trị đơn gồm phí giao hàng, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_034_metadata$::jsonb,
$ent_034_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 14,
  "runtime_ms": 16.519,
  "column_types": [
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "customer_id",
      "postgres_type": "integer"
    },
    {
      "name": "total_amount",
      "postgres_type": "numeric(15,2)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "order_id": 625,
        "customer_id": 171,
        "total_amount": "5587607.90"
      },
      {
        "order_id": 641,
        "customer_id": 76,
        "total_amount": "2619395.42"
      },
      {
        "order_id": 662,
        "customer_id": 45,
        "total_amount": "3935974.90"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "inventory_transactions",
    "order_items",
    "orders",
    "payments",
    "refunds"
  ],
  "process_wall_ms": 90.329,
  "oracle_row_count": 14,
  "result_sha256": "123bee3f96b56f26e0dc16b97a60bedfcc117219797e08ac5975ce7926ba6c2c",
  "oracle_sha256": "123bee3f96b56f26e0dc16b97a60bedfcc117219797e08ac5975ce7926ba6c2c",
  "repeat_runtime_ms": 15.565,
  "repeat_result_sha256": "123bee3f96b56f26e0dc16b97a60bedfcc117219797e08ac5975ce7926ba6c2c",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Đối chiếu tồn tại trả hàng vật lý với không tồn tại hoàn tiền qua hai quan hệ khác.",
    "primary_skill_group": "S4"
  }
}$ent_034_validation$::jsonb
);

-- ENT-035
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_035_question_id$ENT-035$ent_035_question_id$,
$ent_035_world_id$enterprise_v1$ent_035_world_id$,
$ent_035_title$Hai đơn giá trị lớn nhất tại mỗi kho$ent_035_title$,
$ent_035_question_text$Trong mọi đơn có warehouse_id không NULL, lấy tối đa 2 đơn mỗi kho theo total_amount giảm, order_date tăng, order_id tăng; không giới hạn trạng thái.
Cột kết quả theo thứ tự: warehouse_id, position, order_id, total_amount, order_date.
Sắp xếp: warehouse_id tăng, position tăng.
Quy tắc biên: Không giữ thêm đồng hạng; loại kho NULL.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_035_question_text$,
$ent_035_reference_sql$WITH ranked AS (
 SELECT warehouse_id, ROW_NUMBER() OVER (PARTITION BY warehouse_id
        ORDER BY total_amount DESC,order_date,order_id) AS position, order_id,total_amount,order_date
 FROM orders WHERE warehouse_id IS NOT NULL)
SELECT warehouse_id,position,order_id,total_amount,order_date FROM ranked WHERE position<=2
ORDER BY warehouse_id,position;$ent_035_reference_sql$,
$ent_035_difficulty$medium$ent_035_difficulty$,
$ent_035_primary_skill_group$S5$ent_035_primary_skill_group$,
$ent_035_primary_business_domain$Sales & Orders$ent_035_primary_business_domain$,
$ent_035_skills$[
  "window"
]$ent_035_skills$::jsonb,
NULL,
$ent_035_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Trong mọi đơn có warehouse_id không NULL, lấy tối đa 2 đơn mỗi kho theo total_amount giảm, order_date tăng, order_id tăng; không giới hạn trạng thái.",
  "output_grain": "Một đơn được chọn tại mỗi kho",
  "tables_used": [
    "orders"
  ],
  "difficulty_reason": "Xếp hạng trong từng kho rồi lọc top 2; tie được phá bằng ngày và ID.",
  "order_by": "warehouse_id tăng, position tăng",
  "edge_cases": "Không giữ thêm đồng hạng; loại kho NULL.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": "Tối đa 2 dòng mỗi kho.",
  "logic_signature": {
    "goal": "Hai đơn giá trị lớn nhất tại mỗi kho",
    "central_table": "orders",
    "grain": "Một đơn được chọn tại mỗi kho",
    "transformation": "partition warehouse row number top two order value",
    "predicate": "Trong mọi đơn có warehouse_id không NULL, lấy tối đa 2 đơn mỗi kho theo total_amount giảm, order_date tăng, order_id tăng; không giới hạn trạng thái.",
    "edge_cases": "Không giữ thêm đồng hạng; loại kho NULL."
  },
  "output_columns": [
    {
      "name": "warehouse_id",
      "meaning": "Mã kho"
    },
    {
      "name": "position",
      "meaning": "Vị trí theo thứ tự xác định trong đề"
    },
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "total_amount",
      "meaning": "Giá trị đơn gồm phí giao hàng, VND"
    },
    {
      "name": "order_date",
      "meaning": "Thời điểm đặt đơn"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_035_metadata$::jsonb,
$ent_035_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 16,
  "runtime_ms": 5.906,
  "column_types": [
    {
      "name": "warehouse_id",
      "postgres_type": "integer"
    },
    {
      "name": "position",
      "postgres_type": "bigint"
    },
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "total_amount",
      "postgres_type": "numeric(15,2)"
    },
    {
      "name": "order_date",
      "postgres_type": "timestamp without time zone"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "order_id": 30,
        "position": 1,
        "order_date": "2026-05-06T18:10:00",
        "total_amount": "10129694.90",
        "warehouse_id": 1
      },
      {
        "order_id": 684,
        "position": 2,
        "order_date": "2026-03-26T12:40:00",
        "total_amount": "9393470.88",
        "warehouse_id": 1
      },
      {
        "order_id": 852,
        "position": 1,
        "order_date": "2026-01-28T13:00:00",
        "total_amount": "11368673.92",
        "warehouse_id": 2
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "orders"
  ],
  "process_wall_ms": 81.128,
  "oracle_row_count": 16,
  "result_sha256": "1655c5d93dc299f34d34bdaae1ea09bae958d6ed3a4822ae6d516dfb862186ca",
  "oracle_sha256": "1655c5d93dc299f34d34bdaae1ea09bae958d6ed3a4822ae6d516dfb862186ca",
  "repeat_runtime_ms": 5.919,
  "repeat_result_sha256": "1655c5d93dc299f34d34bdaae1ea09bae958d6ed3a4822ae6d516dfb862186ca",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Xếp hạng trong từng kho rồi lọc top 2; tie được phá bằng ngày và ID.",
    "primary_skill_group": "S5"
  }
}$ent_035_validation$::jsonb
);

-- ENT-036
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_036_question_id$ENT-036$ent_036_question_id$,
$ent_036_world_id$enterprise_v1$ent_036_world_id$,
$ent_036_title$Ba mức giá cao nhất trong từng danh mục$ent_036_title$,
$ent_036_question_text$Trong toàn bộ sản phẩm, lấy sản phẩm thuộc 3 mức list_price cao nhất khác nhau mỗi category_id. Các sản phẩm đồng giá có cùng hạng và đều được giữ.
Cột kết quả theo thứ tự: category_id, price_rank, product_id, list_price.
Sắp xếp: category_id tăng, price_rank tăng, product_id tăng.
Quy tắc biên: Giữ mọi đồng hạng; có thể hơn 3 sản phẩm mỗi danh mục.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_036_question_text$,
$ent_036_reference_sql$WITH ranked AS (
 SELECT category_id,DENSE_RANK() OVER (PARTITION BY category_id ORDER BY list_price DESC) AS price_rank,
        product_id,list_price FROM products)
SELECT category_id,price_rank,product_id,list_price FROM ranked WHERE price_rank<=3
ORDER BY category_id,price_rank,product_id;$ent_036_reference_sql$,
$ent_036_difficulty$medium$ent_036_difficulty$,
$ent_036_primary_skill_group$S5$ent_036_primary_skill_group$,
$ent_036_primary_business_domain$Product & Inventory$ent_036_primary_business_domain$,
$ent_036_skills$[
  "window"
]$ent_036_skills$::jsonb,
NULL,
$ent_036_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Trong toàn bộ sản phẩm, lấy sản phẩm thuộc 3 mức list_price cao nhất khác nhau mỗi category_id. Các sản phẩm đồng giá có cùng hạng và đều được giữ.",
  "output_grain": "Một sản phẩm thuộc mức giá được chọn",
  "tables_used": [
    "products"
  ],
  "difficulty_reason": "Cần DENSE_RANK theo danh mục để giữ đầy đủ đồng giá.",
  "order_by": "category_id tăng, price_rank tăng, product_id tăng",
  "edge_cases": "Giữ mọi đồng hạng; có thể hơn 3 sản phẩm mỗi danh mục.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": "Tối đa 3 mức giá mỗi danh mục.",
  "logic_signature": {
    "goal": "Ba mức giá cao nhất trong từng danh mục",
    "central_table": "products",
    "grain": "Một sản phẩm thuộc mức giá được chọn",
    "transformation": "category dense rank price bands",
    "predicate": "Trong toàn bộ sản phẩm, lấy sản phẩm thuộc 3 mức list_price cao nhất khác nhau mỗi category_id. Các sản phẩm đồng giá có cùng hạng và đều được giữ.",
    "edge_cases": "Giữ mọi đồng hạng; có thể hơn 3 sản phẩm mỗi danh mục."
  },
  "output_columns": [
    {
      "name": "category_id",
      "meaning": "Mã danh mục trực tiếp"
    },
    {
      "name": "price_rank",
      "meaning": "Hạng mức giá khác nhau trong danh mục; đồng giá cùng hạng"
    },
    {
      "name": "product_id",
      "meaning": "Mã sản phẩm"
    },
    {
      "name": "list_price",
      "meaning": "Giá niêm yết một đơn vị, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_036_metadata$::jsonb,
$ent_036_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 60,
  "runtime_ms": 4.67,
  "column_types": [
    {
      "name": "category_id",
      "postgres_type": "integer"
    },
    {
      "name": "price_rank",
      "postgres_type": "bigint"
    },
    {
      "name": "product_id",
      "postgres_type": "integer"
    },
    {
      "name": "list_price",
      "postgres_type": "numeric(15,2)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "list_price": "1139227.89",
        "price_rank": 1,
        "product_id": 93,
        "category_id": 1
      },
      {
        "list_price": "1129240.04",
        "price_rank": 2,
        "product_id": 182,
        "category_id": 1
      },
      {
        "list_price": "888398.19",
        "price_rank": 3,
        "product_id": 102,
        "category_id": 1
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "products"
  ],
  "process_wall_ms": 71.359,
  "oracle_row_count": 60,
  "result_sha256": "73f840c06a14aa628ba338b97fbe0d64c2de049447b297bfb0181b84f156e637",
  "oracle_sha256": "73f840c06a14aa628ba338b97fbe0d64c2de049447b297bfb0181b84f156e637",
  "repeat_runtime_ms": 4.877,
  "repeat_result_sha256": "73f840c06a14aa628ba338b97fbe0d64c2de049447b297bfb0181b84f156e637",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần DENSE_RANK theo danh mục để giữ đầy đủ đồng giá.",
    "primary_skill_group": "S5"
  }
}$ent_036_validation$::jsonb
);

-- ENT-037
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_037_question_id$ENT-037$ent_037_question_id$,
$ent_037_world_id$enterprise_v1$ent_037_world_id$,
$ent_037_title$Biến động lương giữa hai mốc liên tiếp$ent_037_title$,
$ent_037_question_text$Với mỗi bản ghi salary_history ngoài bản ghi đầu của nhân viên, trả mức lương trước, mới và phần trăm thay đổi. Thứ tự lịch sử là effective_date, salary_history_id.
Cột kết quả theo thứ tự: employee_id, effective_date, previous_salary, salary, change_pct.
Sắp xếp: employee_id tăng, effective_date tăng.
Quy tắc biên: Bỏ mốc đầu; phần trăm làm tròn 2 chữ số.
Thời gian: effective_date, salary_history_id.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_037_question_text$,
$ent_037_reference_sql$WITH previous AS (
 SELECT employee_id,effective_date,salary,
 LAG(salary) OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS previous_salary
 FROM salary_history)
SELECT employee_id,effective_date,previous_salary,salary,
       ROUND(100.0*(salary-previous_salary)/previous_salary,2) AS change_pct
FROM previous WHERE previous_salary IS NOT NULL ORDER BY employee_id,effective_date;$ent_037_reference_sql$,
$ent_037_difficulty$medium$ent_037_difficulty$,
$ent_037_primary_skill_group$S5$ent_037_primary_skill_group$,
$ent_037_primary_business_domain$Human Resources$ent_037_primary_business_domain$,
$ent_037_skills$[
  "window"
]$ent_037_skills$::jsonb,
NULL,
$ent_037_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Với mỗi bản ghi salary_history ngoài bản ghi đầu của nhân viên, trả mức lương trước, mới và phần trăm thay đổi. Thứ tự lịch sử là effective_date, salary_history_id.",
  "output_grain": "Một mốc lương có mốc trước",
  "tables_used": [
    "salary_history"
  ],
  "difficulty_reason": "Dùng LAG để so sánh hai mốc kề nhau; chưa tìm chuỗi tăng nhiều lần.",
  "order_by": "employee_id tăng, effective_date tăng",
  "edge_cases": "Bỏ mốc đầu; phần trăm làm tròn 2 chữ số.",
  "time_basis": "effective_date, salary_history_id.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Biến động lương giữa hai mốc liên tiếp",
    "central_table": "salary_history",
    "grain": "Một mốc lương có mốc trước",
    "transformation": "salary lag adjacent event percent change",
    "predicate": "Với mỗi bản ghi salary_history ngoài bản ghi đầu của nhân viên, trả mức lương trước, mới và phần trăm thay đổi. Thứ tự lịch sử là effective_date, salary_history_id.",
    "edge_cases": "Bỏ mốc đầu; phần trăm làm tròn 2 chữ số."
  },
  "output_columns": [
    {
      "name": "employee_id",
      "meaning": "Mã nhân viên"
    },
    {
      "name": "effective_date",
      "meaning": "Ngày bắt đầu áp dụng mức lương"
    },
    {
      "name": "previous_salary",
      "meaning": "Mức lương tại mốc liền trước, VND"
    },
    {
      "name": "salary",
      "meaning": "Mức lương có hiệu lực ở mốc mới, VND"
    },
    {
      "name": "change_pct",
      "meaning": "Phần trăm thay đổi so với mốc trước"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_037_metadata$::jsonb,
$ent_037_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 100,
  "runtime_ms": 3.715,
  "column_types": [
    {
      "name": "employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "effective_date",
      "postgres_type": "date"
    },
    {
      "name": "previous_salary",
      "postgres_type": "numeric"
    },
    {
      "name": "salary",
      "postgres_type": "numeric(15,2)"
    },
    {
      "name": "change_pct",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "salary": "71000000.00",
        "change_pct": "8.70",
        "employee_id": 1,
        "effective_date": "2023-11-11",
        "previous_salary": "65320000.00"
      },
      {
        "salary": "70840000.00",
        "change_pct": "9.52",
        "employee_id": 2,
        "effective_date": "2021-10-03",
        "previous_salary": "64680000.00"
      },
      {
        "salary": "77000000.00",
        "change_pct": "8.70",
        "employee_id": 2,
        "effective_date": "2022-05-31",
        "previous_salary": "70840000.00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "salary_history"
  ],
  "process_wall_ms": 77.508,
  "oracle_row_count": 100,
  "result_sha256": "690ea297aae924c122bdc2a1c812de57f8bebeb72815cd9f86189d26d059b748",
  "oracle_sha256": "690ea297aae924c122bdc2a1c812de57f8bebeb72815cd9f86189d26d059b748",
  "repeat_runtime_ms": 4.766,
  "repeat_result_sha256": "690ea297aae924c122bdc2a1c812de57f8bebeb72815cd9f86189d26d059b748",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Dùng LAG để so sánh hai mốc kề nhau; chưa tìm chuỗi tăng nhiều lần.",
    "primary_skill_group": "S5"
  }
}$ent_037_validation$::jsonb
);

-- ENT-038
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_038_question_id$ENT-038$ent_038_question_id$,
$ent_038_world_id$enterprise_v1$ent_038_world_id$,
$ent_038_title$Biến động giá trị đơn đã giao theo tháng đặt$ent_038_title$,
$ent_038_question_text$Nhóm đơn status='delivered' theo tháng order_date, tính tổng total_amount và phần trăm thay đổi so với tháng có dữ liệu ngay trước trong kết quả.
Cột kết quả theo thứ tự: month, order_value, previous_value, change_pct.
Sắp xếp: month tăng.
Quy tắc biên: Tháng đầu hoặc previous_value=0 có change_pct=NULL; không tự thêm tháng trống; làm tròn 2 chữ số.
Thời gian: order_date; không dùng delivered_at.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_038_question_text$,
$ent_038_reference_sql$WITH monthly AS (
 SELECT DATE_TRUNC('month',order_date)::date AS month,SUM(total_amount) AS order_value
 FROM orders WHERE status='delivered' GROUP BY 1), compared AS (
 SELECT month,order_value,LAG(order_value) OVER (ORDER BY month) AS previous_value FROM monthly)
SELECT month,order_value,previous_value,
       ROUND(100.0*(order_value-previous_value)/NULLIF(previous_value,0),2) AS change_pct
FROM compared ORDER BY month;$ent_038_reference_sql$,
$ent_038_difficulty$medium$ent_038_difficulty$,
$ent_038_primary_skill_group$S5$ent_038_primary_skill_group$,
$ent_038_primary_business_domain$Sales & Orders$ent_038_primary_business_domain$,
$ent_038_skills$[
  "window"
]$ent_038_skills$::jsonb,
NULL,
$ent_038_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Nhóm đơn status='delivered' theo tháng order_date, tính tổng total_amount và phần trăm thay đổi so với tháng có dữ liệu ngay trước trong kết quả.",
  "output_grain": "Một tháng có đơn delivered",
  "tables_used": [
    "orders"
  ],
  "difficulty_reason": "Tổng hợp tháng rồi so sánh nhóm liền trước bằng LAG.",
  "order_by": "month tăng",
  "edge_cases": "Tháng đầu hoặc previous_value=0 có change_pct=NULL; không tự thêm tháng trống; làm tròn 2 chữ số.",
  "time_basis": "order_date; không dùng delivered_at.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Biến động giá trị đơn đã giao theo tháng đặt",
    "central_table": "orders",
    "grain": "Một tháng có đơn delivered",
    "transformation": "monthly delivered order value aggregate lag",
    "predicate": "Nhóm đơn status='delivered' theo tháng order_date, tính tổng total_amount và phần trăm thay đổi so với tháng có dữ liệu ngay trước trong kết quả.",
    "edge_cases": "Tháng đầu hoặc previous_value=0 có change_pct=NULL; không tự thêm tháng trống; làm tròn 2 chữ số."
  },
  "output_columns": [
    {
      "name": "month",
      "meaning": "Ngày đầu tháng"
    },
    {
      "name": "order_value",
      "meaning": "Tổng giá trị đơn, không phải tiền thực thu, VND"
    },
    {
      "name": "previous_value",
      "meaning": "Giá trị của tháng có dữ liệu liền trước, VND"
    },
    {
      "name": "change_pct",
      "meaning": "Phần trăm thay đổi so với mốc trước"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_038_metadata$::jsonb,
$ent_038_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 19,
  "runtime_ms": 5.223,
  "column_types": [
    {
      "name": "month",
      "postgres_type": "date"
    },
    {
      "name": "order_value",
      "postgres_type": "numeric"
    },
    {
      "name": "previous_value",
      "postgres_type": "numeric"
    },
    {
      "name": "change_pct",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "month": "2025-03-01",
        "change_pct": null,
        "order_value": "83625165.97",
        "previous_value": null
      },
      {
        "month": "2025-04-01",
        "change_pct": "3.36",
        "order_value": "86439014.58",
        "previous_value": "83625165.97"
      },
      {
        "month": "2025-05-01",
        "change_pct": "-0.86",
        "order_value": "85693641.01",
        "previous_value": "86439014.58"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "orders"
  ],
  "process_wall_ms": 75.496,
  "oracle_row_count": 19,
  "result_sha256": "a2b52b987964458136aa13b3be5ab8ce855c27ed8a46b19a6ea2e4fc7c6055c7",
  "oracle_sha256": "a2b52b987964458136aa13b3be5ab8ce855c27ed8a46b19a6ea2e4fc7c6055c7",
  "repeat_runtime_ms": 4.945,
  "repeat_result_sha256": "a2b52b987964458136aa13b3be5ab8ce855c27ed8a46b19a6ea2e4fc7c6055c7",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Tổng hợp tháng rồi so sánh nhóm liền trước bằng LAG.",
    "primary_skill_group": "S5"
  }
}$ent_038_validation$::jsonb
);

-- ENT-039
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_039_question_id$ENT-039$ent_039_question_id$,
$ent_039_world_id$enterprise_v1$ent_039_world_id$,
$ent_039_title$Tiền thu thành công lũy kế theo tháng$ent_039_title$,
$ent_039_question_text$Nhóm payments payment_status='success' theo tháng attempted_at; trả tiền thu tháng và tổng tiền thu lũy kế từ tháng đầu. Không trừ refunds.
Cột kết quả theo thứ tự: month, collected_amount, cumulative_collected.
Sắp xếp: month tăng.
Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.
Thời gian: attempted_at của success; chỉ tháng có success.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_039_question_text$,
$ent_039_reference_sql$WITH monthly AS (
 SELECT DATE_TRUNC('month',attempted_at)::date AS month,SUM(amount) AS collected_amount
 FROM payments WHERE payment_status='success' GROUP BY 1)
SELECT month,collected_amount,SUM(collected_amount) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING) AS cumulative_collected
FROM monthly ORDER BY month;$ent_039_reference_sql$,
$ent_039_difficulty$medium$ent_039_difficulty$,
$ent_039_primary_skill_group$S5$ent_039_primary_skill_group$,
$ent_039_primary_business_domain$Finance$ent_039_primary_business_domain$,
$ent_039_skills$[
  "window"
]$ent_039_skills$::jsonb,
NULL,
$ent_039_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Nhóm payments payment_status='success' theo tháng attempted_at; trả tiền thu tháng và tổng tiền thu lũy kế từ tháng đầu. Không trừ refunds.",
  "output_grain": "Một tháng có thanh toán success",
  "tables_used": [
    "payments"
  ],
  "difficulty_reason": "Tổng hợp tiền thu thực tế rồi tính lũy kế trên các nhóm tháng.",
  "order_by": "month tăng",
  "edge_cases": "Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.",
  "time_basis": "attempted_at của success; chỉ tháng có success.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Tiền thu thành công lũy kế theo tháng",
    "central_table": "payments",
    "grain": "Một tháng có thanh toán success",
    "transformation": "monthly successful cash aggregate running total",
    "predicate": "Nhóm payments payment_status='success' theo tháng attempted_at; trả tiền thu tháng và tổng tiền thu lũy kế từ tháng đầu. Không trừ refunds.",
    "edge_cases": ""
  },
  "output_columns": [
    {
      "name": "month",
      "meaning": "Ngày đầu tháng"
    },
    {
      "name": "collected_amount",
      "meaning": "Tiền payment success trong tháng, VND"
    },
    {
      "name": "cumulative_collected",
      "meaning": "Tiền payment success lũy kế, chưa trừ refund, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_039_metadata$::jsonb,
$ent_039_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 19,
  "runtime_ms": 5.073,
  "column_types": [
    {
      "name": "month",
      "postgres_type": "date"
    },
    {
      "name": "collected_amount",
      "postgres_type": "numeric"
    },
    {
      "name": "cumulative_collected",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "month": "2025-03-01",
        "collected_amount": "196393080.55",
        "cumulative_collected": "196393080.55"
      },
      {
        "month": "2025-04-01",
        "collected_amount": "190150658.57",
        "cumulative_collected": "386543739.12"
      },
      {
        "month": "2025-05-01",
        "collected_amount": "186231576.53",
        "cumulative_collected": "572775315.65"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "payments"
  ],
  "process_wall_ms": 73.952,
  "oracle_row_count": 19,
  "result_sha256": "c3df6f552d1ccc06651048723c0bd96b0b0aedd2bb9a84e9aa140efd52a5419e",
  "oracle_sha256": "c3df6f552d1ccc06651048723c0bd96b0b0aedd2bb9a84e9aa140efd52a5419e",
  "repeat_runtime_ms": 5.033,
  "repeat_result_sha256": "c3df6f552d1ccc06651048723c0bd96b0b0aedd2bb9a84e9aa140efd52a5419e",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Tổng hợp tiền thu thực tế rồi tính lũy kế trên các nhóm tháng.",
    "primary_skill_group": "S5"
  }
}$ent_039_validation$::jsonb
);

-- ENT-040
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_040_question_id$ENT-040$ent_040_question_id$,
$ent_040_world_id$enterprise_v1$ent_040_world_id$,
$ent_040_title$Khoảng cách giữa các lần đặt của khách$ent_040_title$,
$ent_040_question_text$Với mỗi đơn ngoài đơn đầu của khách, trả order_id trước đó và số ngày giữa hai order_date liên tiếp. Bao gồm mọi trạng thái; thứ tự order_date,order_id.
Cột kết quả theo thứ tự: customer_id, order_id, previous_order_id, gap_days.
Sắp xếp: customer_id tăng, order_date tăng, order_id tăng.
Quy tắc biên: Bỏ đơn đầu; gap_days tính cả phần lẻ ngày, làm tròn 2 chữ số.
Thời gian: order_date,order_id.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_040_question_text$,
$ent_040_reference_sql$WITH previous AS (
 SELECT customer_id,order_id,order_date,
 LAG(order_id) OVER (PARTITION BY customer_id ORDER BY order_date,order_id) AS previous_order_id,
 LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date,order_id) AS previous_date FROM orders)
SELECT customer_id,order_id,previous_order_id,
       ROUND(EXTRACT(EPOCH FROM order_date-previous_date)/86400,2) AS gap_days
FROM previous WHERE previous_order_id IS NOT NULL ORDER BY customer_id,order_date,order_id;$ent_040_reference_sql$,
$ent_040_difficulty$medium$ent_040_difficulty$,
$ent_040_primary_skill_group$S5$ent_040_primary_skill_group$,
$ent_040_primary_business_domain$Customer Management$ent_040_primary_business_domain$,
$ent_040_skills$[
  "window"
]$ent_040_skills$::jsonb,
NULL,
$ent_040_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Với mỗi đơn ngoài đơn đầu của khách, trả order_id trước đó và số ngày giữa hai order_date liên tiếp. Bao gồm mọi trạng thái; thứ tự order_date,order_id.",
  "output_grain": "Một đơn có đơn trước của cùng khách",
  "tables_used": [
    "orders"
  ],
  "difficulty_reason": "Cần LAG theo khách để xác định đơn kề trước và tính khoảng cách.",
  "order_by": "customer_id tăng, order_date tăng, order_id tăng",
  "edge_cases": "Bỏ đơn đầu; gap_days tính cả phần lẻ ngày, làm tròn 2 chữ số.",
  "time_basis": "order_date,order_id.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Khoảng cách giữa các lần đặt của khách",
    "central_table": "orders",
    "grain": "Một đơn có đơn trước của cùng khách",
    "transformation": "customer repeat order lag fractional day gap",
    "predicate": "Với mỗi đơn ngoài đơn đầu của khách, trả order_id trước đó và số ngày giữa hai order_date liên tiếp. Bao gồm mọi trạng thái; thứ tự order_date,order_id.",
    "edge_cases": "Bỏ đơn đầu; gap_days tính cả phần lẻ ngày, làm tròn 2 chữ số."
  },
  "output_columns": [
    {
      "name": "customer_id",
      "meaning": "Mã khách hàng"
    },
    {
      "name": "order_id",
      "meaning": "Mã đơn hàng"
    },
    {
      "name": "previous_order_id",
      "meaning": "Mã đơn liền trước của cùng khách"
    },
    {
      "name": "gap_days",
      "meaning": "Khoảng cách ngày có phần lẻ"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_040_metadata$::jsonb,
$ent_040_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 737,
  "runtime_ms": 9.605,
  "column_types": [
    {
      "name": "customer_id",
      "postgres_type": "integer"
    },
    {
      "name": "order_id",
      "postgres_type": "integer"
    },
    {
      "name": "previous_order_id",
      "postgres_type": "integer"
    },
    {
      "name": "gap_days",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "gap_days": "40.04",
        "order_id": 669,
        "customer_id": 1,
        "previous_order_id": 100
      },
      {
        "gap_days": "11.80",
        "order_id": 566,
        "customer_id": 1,
        "previous_order_id": 669
      },
      {
        "gap_days": "71.38",
        "order_id": 918,
        "customer_id": 1,
        "previous_order_id": 566
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "orders"
  ],
  "process_wall_ms": 78.451,
  "oracle_row_count": 737,
  "result_sha256": "e5168f81344f0e30fec9a2e5dede5519335ac24458b01e1820fcaf72b8e9e665",
  "oracle_sha256": "e5168f81344f0e30fec9a2e5dede5519335ac24458b01e1820fcaf72b8e9e665",
  "repeat_runtime_ms": 8.996,
  "repeat_result_sha256": "e5168f81344f0e30fec9a2e5dede5519335ac24458b01e1820fcaf72b8e9e665",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần LAG theo khách để xác định đơn kề trước và tính khoảng cách.",
    "primary_skill_group": "S5"
  }
}$ent_040_validation$::jsonb
);

-- ENT-041
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_041_question_id$ENT-041$ent_041_question_id$,
$ent_041_world_id$enterprise_v1$ent_041_world_id$,
$ent_041_title$Nguồn cung phủ đầy đủ hàng bán và kho có tồn$ent_041_title$,
$ent_041_question_text$Tìm nhà cung cấp có ít nhất 2 sản phẩm đang hoạt động. Mỗi sản phẩm đang hoạt động phải có ít nhất một dòng thuộc đơn delivered; tại mọi kho từng có đơn delivered chứa sản phẩm đó, tổng quantity_change của chính sản phẩm tại kho đó phải >0. Sản phẩm không hoạt động không tham gia điều kiện.
Cột kết quả theo thứ tự: supplier_id, supplier_name.
Sắp xếp: supplier_id tăng.
Quy tắc biên: Kho không có giao dịch được xem có tồn 0; nhà cung cấp ít hơn 2 hàng active bị loại.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_041_question_text$,
$ent_041_reference_sql$SELECT s.supplier_id,s.supplier_name FROM suppliers s
WHERE (SELECT COUNT(*) FROM products p WHERE p.supplier_id=s.supplier_id AND p.is_active)>=2
AND NOT EXISTS (
 SELECT 1 FROM products p WHERE p.supplier_id=s.supplier_id AND p.is_active AND (
  NOT EXISTS (SELECT 1 FROM order_items i JOIN orders o ON o.order_id=i.order_id
              WHERE i.product_id=p.product_id AND o.status='delivered')
  OR EXISTS (
   SELECT 1 FROM order_items i JOIN orders o ON o.order_id=i.order_id
   WHERE i.product_id=p.product_id AND o.status='delivered' AND NOT EXISTS (
    SELECT 1 FROM inventory_transactions t WHERE t.product_id=p.product_id AND t.warehouse_id=o.warehouse_id
    GROUP BY t.product_id,t.warehouse_id HAVING SUM(t.quantity_change)>0))))
ORDER BY s.supplier_id;$ent_041_reference_sql$,
$ent_041_difficulty$hard$ent_041_difficulty$,
$ent_041_primary_skill_group$S4$ent_041_primary_skill_group$,
$ent_041_primary_business_domain$Product & Inventory$ent_041_primary_business_domain$,
$ent_041_skills$[
  "anti_existence"
]$ent_041_skills$::jsonb,
NULL,
$ent_041_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Tìm nhà cung cấp có ít nhất 2 sản phẩm đang hoạt động. Mỗi sản phẩm đang hoạt động phải có ít nhất một dòng thuộc đơn delivered; tại mọi kho từng có đơn delivered chứa sản phẩm đó, tổng quantity_change của chính sản phẩm tại kho đó phải >0. Sản phẩm không hoạt động không tham gia điều kiện.",
  "output_grain": "Một nhà cung cấp đạt phép chia quan hệ",
  "tables_used": [
    "suppliers",
    "products",
    "order_items",
    "orders",
    "inventory_transactions"
  ],
  "difficulty_reason": "Phép lượng hóa mọi sản phẩm lồng mọi kho đã giao, kết hợp tồn tại bán và tổng tồn tương quan. Cần chống điều kiện đúng trên tập rỗng ở cả hai tầng.",
  "order_by": "supplier_id tăng",
  "edge_cases": "Kho không có giao dịch được xem có tồn 0; nhà cung cấp ít hơn 2 hàng active bị loại.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Nguồn cung phủ đầy đủ hàng bán và kho có tồn",
    "central_table": "suppliers",
    "grain": "Một nhà cung cấp đạt phép chia quan hệ",
    "transformation": "supplier all active products delivered exposure all exposed warehouses positive stock",
    "predicate": "Tìm nhà cung cấp có ít nhất 2 sản phẩm đang hoạt động. Mỗi sản phẩm đang hoạt động phải có ít nhất một dòng thuộc đơn delivered; tại mọi kho từng có đơn delivered chứa sản phẩm đó, tổng quantity_change của chính sản phẩm tại kho đó phải >0. Sản phẩm không hoạt động không tham gia điều kiện.",
    "edge_cases": "Kho không có giao dịch được xem có tồn 0; nhà cung cấp ít hơn 2 hàng active bị loại."
  },
  "output_columns": [
    {
      "name": "supplier_id",
      "meaning": "Mã nhà cung cấp"
    },
    {
      "name": "supplier_name",
      "meaning": "Tên nhà cung cấp"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_041_metadata$::jsonb,
$ent_041_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 16,
  "runtime_ms": 27.321,
  "column_types": [
    {
      "name": "supplier_id",
      "postgres_type": "integer"
    },
    {
      "name": "supplier_name",
      "postgres_type": "character varying(150)"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "supplier_id": 1,
        "supplier_name": "Supplier 01"
      },
      {
        "supplier_id": 5,
        "supplier_name": "Supplier 05"
      },
      {
        "supplier_id": 7,
        "supplier_name": "Supplier 07"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "inventory_transactions",
    "order_items",
    "orders",
    "products",
    "suppliers"
  ],
  "process_wall_ms": 96.046,
  "oracle_row_count": 16,
  "result_sha256": "4314436334dc764f8d5869bce5a9ec1884dd2412b46721ed5821739059ce160e",
  "oracle_sha256": "4314436334dc764f8d5869bce5a9ec1884dd2412b46721ed5821739059ce160e",
  "repeat_runtime_ms": 29.618,
  "repeat_result_sha256": "4314436334dc764f8d5869bce5a9ec1884dd2412b46721ed5821739059ce160e",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Phép lượng hóa mọi sản phẩm lồng mọi kho đã giao, kết hợp tồn tại bán và tổng tồn tương quan. Cần chống điều kiện đúng trên tập rỗng ở cả hai tầng.",
    "primary_skill_group": "S4"
  }
}$ent_041_validation$::jsonb
);

-- ENT-042
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_042_question_id$ENT-042$ent_042_question_id$,
$ent_042_world_id$enterprise_v1$ent_042_world_id$,
$ent_042_title$Chuỗi thắng tháng dài nhất của nhân viên$ent_042_title$,
$ent_042_question_text$Trong đơn delivered có employee_id không NULL, tính giá trị total_amount theo nhân viên và tháng order_date. Mỗi tháng chọn đúng một người thắng theo tổng giảm rồi employee_id tăng. Với mỗi người từng thắng, trả chuỗi thắng ở các tháng lịch liên tiếp dài nhất; nếu hòa chọn chuỗi bắt đầu sớm hơn.
Cột kết quả theo thứ tự: employee_id, start_month, end_month, streak_months.
Sắp xếp: employee_id tăng.
Quy tắc biên: Tháng không có đơn eligible cắt chuỗi; tie thắng tháng chọn ID nhỏ; tie chuỗi chọn bắt đầu sớm.
Thời gian: Tháng order_date; liên tiếp theo tháng lịch.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_042_question_text$,
$ent_042_reference_sql$WITH totals AS (
 SELECT DATE_TRUNC('month',order_date)::date AS month,employee_id,SUM(total_amount) AS value
 FROM orders WHERE status='delivered' AND employee_id IS NOT NULL GROUP BY 1,2), ranked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY month ORDER BY value DESC,employee_id) AS pos FROM totals), wins AS (
 SELECT employee_id,month,
 (EXTRACT(YEAR FROM month)::int*12+EXTRACT(MONTH FROM month)::int)
 -ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY month) AS island
 FROM ranked WHERE pos=1), streaks AS (
 SELECT employee_id,MIN(month) AS start_month,MAX(month) AS end_month,COUNT(*) AS streak_months
 FROM wins GROUP BY employee_id,island), picked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY streak_months DESC,start_month) AS pos FROM streaks)
SELECT employee_id,start_month,end_month,streak_months FROM picked WHERE pos=1 ORDER BY employee_id;$ent_042_reference_sql$,
$ent_042_difficulty$hard$ent_042_difficulty$,
$ent_042_primary_skill_group$S5$ent_042_primary_skill_group$,
$ent_042_primary_business_domain$Sales & Orders$ent_042_primary_business_domain$,
$ent_042_skills$[
  "window"
]$ent_042_skills$::jsonb,
NULL,
$ent_042_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Trong đơn delivered có employee_id không NULL, tính giá trị total_amount theo nhân viên và tháng order_date. Mỗi tháng chọn đúng một người thắng theo tổng giảm rồi employee_id tăng. Với mỗi người từng thắng, trả chuỗi thắng ở các tháng lịch liên tiếp dài nhất; nếu hòa chọn chuỗi bắt đầu sớm hơn.",
  "output_grain": "Một nhân viên từng thắng tháng",
  "tables_used": [
    "orders"
  ],
  "difficulty_reason": "Phải tổng hợp, chọn người thắng từng tháng, phát hiện khoảng đứt theo lịch rồi chọn chuỗi dài nhất từng người. Một ranking đơn lẻ không đủ.",
  "order_by": "employee_id tăng",
  "edge_cases": "Tháng không có đơn eligible cắt chuỗi; tie thắng tháng chọn ID nhỏ; tie chuỗi chọn bắt đầu sớm.",
  "time_basis": "Tháng order_date; liên tiếp theo tháng lịch.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Chuỗi thắng tháng dài nhất của nhân viên",
    "central_table": "orders",
    "grain": "Một nhân viên từng thắng tháng",
    "transformation": "monthly employee sums deterministic winner calendar consecutive islands longest",
    "predicate": "Trong đơn delivered có employee_id không NULL, tính giá trị total_amount theo nhân viên và tháng order_date. Mỗi tháng chọn đúng một người thắng theo tổng giảm rồi employee_id tăng. Với mỗi người từng thắng, trả chuỗi thắng ở các tháng lịch liên tiếp dài nhất; nếu hòa chọn chuỗi bắt đầu sớm hơn.",
    "edge_cases": "Tháng không có đơn eligible cắt chuỗi; tie thắng tháng chọn ID nhỏ; tie chuỗi chọn bắt đầu sớm."
  },
  "output_columns": [
    {
      "name": "employee_id",
      "meaning": "Mã nhân viên"
    },
    {
      "name": "start_month",
      "meaning": "Ngày đầu tháng bắt đầu đoạn"
    },
    {
      "name": "end_month",
      "meaning": "Ngày đầu tháng kết thúc đoạn"
    },
    {
      "name": "streak_months",
      "meaning": "Số tháng lịch liên tiếp trong đoạn"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_042_metadata$::jsonb,
$ent_042_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 19,
  "runtime_ms": 6.421,
  "column_types": [
    {
      "name": "employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "start_month",
      "postgres_type": "date"
    },
    {
      "name": "end_month",
      "postgres_type": "date"
    },
    {
      "name": "streak_months",
      "postgres_type": "bigint"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "end_month": "2026-03-01",
        "employee_id": 3,
        "start_month": "2026-03-01",
        "streak_months": 1
      },
      {
        "end_month": "2026-09-01",
        "employee_id": 11,
        "start_month": "2026-09-01",
        "streak_months": 1
      },
      {
        "end_month": "2025-08-01",
        "employee_id": 14,
        "start_month": "2025-08-01",
        "streak_months": 1
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "orders"
  ],
  "process_wall_ms": 74.424,
  "oracle_row_count": 19,
  "result_sha256": "9bd8ddffde2c1d2e25e09bf3462420aef207917b10835e008430f924e18d4adb",
  "oracle_sha256": "9bd8ddffde2c1d2e25e09bf3462420aef207917b10835e008430f924e18d4adb",
  "repeat_runtime_ms": 6.797,
  "repeat_result_sha256": "9bd8ddffde2c1d2e25e09bf3462420aef207917b10835e008430f924e18d4adb",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Phải tổng hợp, chọn người thắng từng tháng, phát hiện khoảng đứt theo lịch rồi chọn chuỗi dài nhất từng người. Một ranking đơn lẻ không đủ.",
    "primary_skill_group": "S5"
  }
}$ent_042_validation$::jsonb
);

-- ENT-043
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_043_question_id$ENT-043$ent_043_question_id$,
$ent_043_world_id$enterprise_v1$ent_043_world_id$,
$ent_043_title$Ba cửa sổ ba tháng có tiền ròng lớn nhất$ent_043_title$,
$ent_043_question_text$Gộp tiền vào từ payment success theo attempted_at và tiền ra từ refund completed theo completed_at. Tạo đủ các tháng từ tháng sự kiện sớm nhất đến muộn nhất; tháng trống bằng 0. Tính tiền ròng trong cửa sổ 3 tháng lịch kết thúc mỗi tháng, chỉ giữ cửa sổ đủ 3 tháng. Chọn tối đa 3 cửa sổ có tổng ròng lớn nhất, hòa chọn tháng kết thúc sớm hơn.
Cột kết quả theo thứ tự: start_month, end_month, net_three_months.
Sắp xếp: net_three_months giảm, end_month tăng.
Quy tắc biên: Chỉ completed refund được trừ; không dùng requested_at; không giữ thêm đồng hạng.
Thời gian: attempted_at và completed_at; cửa sổ tháng lịch.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_043_question_text$,
$ent_043_reference_sql$WITH events AS (
 SELECT DATE_TRUNC('month',attempted_at)::date AS month,amount AS delta FROM payments WHERE payment_status='success'
 UNION ALL
 SELECT DATE_TRUNC('month',completed_at)::date,-refund_amount FROM refunds WHERE refund_status='completed'),
calendar AS (
 SELECT GENERATE_SERIES(MIN(month)::timestamp,MAX(month)::timestamp,INTERVAL '1 month')::date AS month FROM events),
monthly AS (
 SELECT c.month,COALESCE(SUM(e.delta),0) AS net FROM calendar c LEFT JOIN events e USING(month) GROUP BY c.month),
rolling AS (
 SELECT month,SUM(net) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS net_three_months,
 COUNT(*) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS months_in_window FROM monthly)
SELECT (month-INTERVAL '2 months')::date AS start_month,month AS end_month,net_three_months
FROM rolling WHERE months_in_window=3 ORDER BY net_three_months DESC,month LIMIT 3;$ent_043_reference_sql$,
$ent_043_difficulty$hard$ent_043_difficulty$,
$ent_043_primary_skill_group$S5$ent_043_primary_skill_group$,
$ent_043_primary_business_domain$Finance$ent_043_primary_business_domain$,
$ent_043_skills$[
  "calendar",
  "window"
]$ent_043_skills$::jsonb,
NULL,
$ent_043_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Gộp tiền vào từ payment success theo attempted_at và tiền ra từ refund completed theo completed_at. Tạo đủ các tháng từ tháng sự kiện sớm nhất đến muộn nhất; tháng trống bằng 0. Tính tiền ròng trong cửa sổ 3 tháng lịch kết thúc mỗi tháng, chỉ giữ cửa sổ đủ 3 tháng. Chọn tối đa 3 cửa sổ có tổng ròng lớn nhất, hòa chọn tháng kết thúc sớm hơn.",
  "output_grain": "Một cửa sổ ba tháng được chọn",
  "tables_used": [
    "payments",
    "refunds"
  ],
  "difficulty_reason": "Cần hợp nhất hai dòng tiền khác ngày ghi nhận, lấp tháng trống, kiểm tra độ dài cửa sổ và xếp hạng tổng trượt. Đây không phải một SUM lũy kế đơn giản.",
  "order_by": "net_three_months giảm, end_month tăng",
  "edge_cases": "Chỉ completed refund được trừ; không dùng requested_at; không giữ thêm đồng hạng.",
  "time_basis": "attempted_at và completed_at; cửa sổ tháng lịch.",
  "result_limit": 3,
  "logic_signature": {
    "goal": "Ba cửa sổ ba tháng có tiền ròng lớn nhất",
    "central_table": "payments",
    "grain": "Một cửa sổ ba tháng được chọn",
    "transformation": "signed cash event union calendar zero fill complete three month rolling top windows",
    "predicate": "Gộp tiền vào từ payment success theo attempted_at và tiền ra từ refund completed theo completed_at. Tạo đủ các tháng từ tháng sự kiện sớm nhất đến muộn nhất; tháng trống bằng 0. Tính tiền ròng trong cửa sổ 3 tháng lịch kết thúc mỗi tháng, chỉ giữ cửa sổ đủ 3 tháng. Chọn tối đa 3 cửa sổ có tổng ròng lớn nhất, hòa chọn tháng kết thúc sớm hơn.",
    "edge_cases": "Chỉ completed refund được trừ; không dùng requested_at; không giữ thêm đồng hạng."
  },
  "output_columns": [
    {
      "name": "start_month",
      "meaning": "Ngày đầu tháng bắt đầu đoạn"
    },
    {
      "name": "end_month",
      "meaning": "Ngày đầu tháng kết thúc đoạn"
    },
    {
      "name": "net_three_months",
      "meaning": "Tiền success trừ completed refund theo ngày sự kiện trong 3 tháng, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_043_metadata$::jsonb,
$ent_043_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 3,
  "runtime_ms": 8.393,
  "column_types": [
    {
      "name": "start_month",
      "postgres_type": "date"
    },
    {
      "name": "end_month",
      "postgres_type": "date"
    },
    {
      "name": "net_three_months",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "end_month": "2025-05-01",
        "start_month": "2025-03-01",
        "net_three_months": "563974974.43"
      },
      {
        "end_month": "2025-06-01",
        "start_month": "2025-04-01",
        "net_three_months": "558633523.93"
      },
      {
        "end_month": "2025-07-01",
        "start_month": "2025-05-01",
        "net_three_months": "520838828.84"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "payments",
    "refunds"
  ],
  "process_wall_ms": 80.019,
  "oracle_row_count": 3,
  "result_sha256": "b73444e148d0a37949de93e9c820ff820ea317e5300b64d70f634d733e457edb",
  "oracle_sha256": "b73444e148d0a37949de93e9c820ff820ea317e5300b64d70f634d733e457edb",
  "repeat_runtime_ms": 7.333,
  "repeat_result_sha256": "b73444e148d0a37949de93e9c820ff820ea317e5300b64d70f634d733e457edb",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần hợp nhất hai dòng tiền khác ngày ghi nhận, lấp tháng trống, kiểm tra độ dài cửa sổ và xếp hạng tổng trượt. Đây không phải một SUM lũy kế đơn giản.",
    "primary_skill_group": "S5"
  }
}$ent_043_validation$::jsonb
);

-- ENT-044
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_044_question_id$ENT-044$ent_044_question_id$,
$ent_044_world_id$enterprise_v1$ent_044_world_id$,
$ent_044_title$Nhóm loại chi nhỏ nhất đạt 80 phần trăm chi phòng$ent_044_title$,
$ent_044_question_text$Trong chi có expense_date thuộc năm 2025, tổng hợp amount theo phòng và expense_category. Xếp loại chi theo tổng giảm, tên loại tăng; với mỗi phòng, giữ tiền tố ngắn nhất mà tổng tích lũy đạt ít nhất 80% tổng chi phòng. Trả từng loại trong tiền tố, vị trí, tiền loại và phần trăm tích lũy.
Cột kết quả theo thứ tự: department_id, position, expense_category, category_amount, cumulative_pct.
Sắp xếp: department_id tăng NULLS LAST, position tăng.
Quy tắc biên: Phòng NULL là một nhóm riêng; làm tròn phần trăm sau khi lọc bằng số chính xác.
Thời gian: expense_date >=2025-01-01 và <2026-01-01.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_044_question_text$,
$ent_044_reference_sql$WITH categories AS (
 SELECT department_id,expense_category,SUM(amount) AS category_amount FROM operating_expenses
 WHERE expense_date>=DATE '2025-01-01' AND expense_date<DATE '2026-01-01' GROUP BY 1,2), ranked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY category_amount DESC,expense_category) AS position,
 SUM(category_amount) OVER (PARTITION BY department_id) AS total,
 SUM(category_amount) OVER (PARTITION BY department_id ORDER BY category_amount DESC,expense_category
 ROWS UNBOUNDED PRECEDING) AS cumulative FROM categories)
SELECT department_id,position,expense_category,category_amount,ROUND(100.0*cumulative/total,2) AS cumulative_pct
FROM ranked WHERE cumulative-category_amount<0.8*total ORDER BY department_id NULLS LAST,position;$ent_044_reference_sql$,
$ent_044_difficulty$hard$ent_044_difficulty$,
$ent_044_primary_skill_group$S5$ent_044_primary_skill_group$,
$ent_044_primary_business_domain$Finance$ent_044_primary_business_domain$,
$ent_044_skills$[
  "window"
]$ent_044_skills$::jsonb,
NULL,
$ent_044_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Trong chi có expense_date thuộc năm 2025, tổng hợp amount theo phòng và expense_category. Xếp loại chi theo tổng giảm, tên loại tăng; với mỗi phòng, giữ tiền tố ngắn nhất mà tổng tích lũy đạt ít nhất 80% tổng chi phòng. Trả từng loại trong tiền tố, vị trí, tiền loại và phần trăm tích lũy.",
  "output_grain": "Một phòng và loại chi trong tiền tố đạt 80%",
  "tables_used": [
    "operating_expenses"
  ],
  "difficulty_reason": "Cần tổng hợp hai cấp, sắp xếp theo đóng góp, tính tích lũy và giữ đúng loại vượt ngưỡng lần đầu. Phải xử lý nhóm phòng NULL và tie để tiền tố tối thiểu xác định.",
  "order_by": "department_id tăng NULLS LAST, position tăng",
  "edge_cases": "Phòng NULL là một nhóm riêng; làm tròn phần trăm sau khi lọc bằng số chính xác.",
  "time_basis": "expense_date >=2025-01-01 và <2026-01-01.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Nhóm loại chi nhỏ nhất đạt 80 phần trăm chi phòng",
    "central_table": "operating_expenses",
    "grain": "Một phòng và loại chi trong tiền tố đạt 80%",
    "transformation": "department category sum sorted prefix threshold crossing minimal cover",
    "predicate": "Trong chi có expense_date thuộc năm 2025, tổng hợp amount theo phòng và expense_category. Xếp loại chi theo tổng giảm, tên loại tăng; với mỗi phòng, giữ tiền tố ngắn nhất mà tổng tích lũy đạt ít nhất 80% tổng chi phòng. Trả từng loại trong tiền tố, vị trí, tiền loại và phần trăm tích lũy.",
    "edge_cases": "Phòng NULL là một nhóm riêng; làm tròn phần trăm sau khi lọc bằng số chính xác."
  },
  "output_columns": [
    {
      "name": "department_id",
      "meaning": "Mã phòng hiện tại"
    },
    {
      "name": "position",
      "meaning": "Vị trí theo thứ tự xác định trong đề"
    },
    {
      "name": "expense_category",
      "meaning": "Loại chi phí"
    },
    {
      "name": "category_amount",
      "meaning": "Tổng amount của loại chi trong phòng, VND"
    },
    {
      "name": "cumulative_pct",
      "meaning": "Phần trăm đóng góp tích lũy"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_044_metadata$::jsonb,
$ent_044_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 26,
  "runtime_ms": 4.405,
  "column_types": [
    {
      "name": "department_id",
      "postgres_type": "integer"
    },
    {
      "name": "position",
      "postgres_type": "bigint"
    },
    {
      "name": "expense_category",
      "postgres_type": "character varying(100)"
    },
    {
      "name": "category_amount",
      "postgres_type": "numeric"
    },
    {
      "name": "cumulative_pct",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "position": 1,
        "department_id": 1,
        "cumulative_pct": "54.50",
        "category_amount": "5191000.00",
        "expense_category": "Utilities"
      },
      {
        "position": 2,
        "department_id": 1,
        "cumulative_pct": "98.15",
        "category_amount": "4158000.00",
        "expense_category": "Training"
      },
      {
        "position": 1,
        "department_id": 2,
        "cumulative_pct": "54.49",
        "category_amount": "13037000.00",
        "expense_category": "Training"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "operating_expenses"
  ],
  "process_wall_ms": 74.539,
  "oracle_row_count": 26,
  "result_sha256": "e41c3325f0b6c131b62e75a37e2a3e170c3f92c43ab34a4cc46fa0396f8e1118",
  "oracle_sha256": "e41c3325f0b6c131b62e75a37e2a3e170c3f92c43ab34a4cc46fa0396f8e1118",
  "repeat_runtime_ms": 4.035,
  "repeat_result_sha256": "e41c3325f0b6c131b62e75a37e2a3e170c3f92c43ab34a4cc46fa0396f8e1118",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần tổng hợp hai cấp, sắp xếp theo đóng góp, tính tích lũy và giữ đúng loại vượt ngưỡng lần đầu. Phải xử lý nhóm phòng NULL và tie để tiền tố tối thiểu xác định.",
    "primary_skill_group": "S5"
  }
}$ent_044_validation$::jsonb
);

-- ENT-045
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_045_question_id$ENT-045$ent_045_question_id$,
$ent_045_world_id$enterprise_v1$ent_045_world_id$,
$ent_045_title$Nhân viên dẫn đầu quý và sản phẩm đóng góp lớn nhất$ent_045_title$,
$ent_045_question_text$Trong đơn delivered được gán nhân viên, tổng line_total theo quý order_date, nhân viên và sản phẩm; chọn sản phẩm có tổng lớn nhất mỗi nhân viên-quý (hòa chọn product_id nhỏ). Tính tổng line_total của nhân viên-quý rồi lấy tối đa 3 nhân viên mỗi quý theo tổng giảm, employee_id tăng. Trả sản phẩm dẫn đầu và tỷ trọng đóng góp của nó. Đây là giá trị hàng theo dòng, không gồm shipping_fee, không trừ refund hoặc trả hàng vật lý, không phải tiền ròng.
Cột kết quả theo thứ tự: quarter, employee_rank, employee_id, merchandise_value, top_product_id, top_product_value, top_share_pct.
Sắp xếp: quarter tăng, employee_rank tăng.
Quy tắc biên: Tổng bằng 0 thì tỷ trọng NULL; phần trăm làm tròn 2 chữ số; không giữ thêm đồng hạng.
Thời gian: Quý order_date; quarter là ngày đầu quý.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_045_question_text$,
$ent_045_reference_sql$WITH products AS (
 SELECT DATE_TRUNC('quarter',o.order_date)::date AS quarter,o.employee_id,i.product_id,SUM(i.line_total) AS product_value
 FROM orders o JOIN order_items i ON i.order_id=o.order_id
 WHERE o.status='delivered' AND o.employee_id IS NOT NULL GROUP BY 1,2,3), product_ranks AS (
 SELECT *,SUM(product_value) OVER (PARTITION BY quarter,employee_id) AS merchandise_value,
 ROW_NUMBER() OVER (PARTITION BY quarter,employee_id ORDER BY product_value DESC,product_id) AS product_pos FROM products),
leaders AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY quarter ORDER BY merchandise_value DESC,employee_id) AS employee_rank
 FROM product_ranks WHERE product_pos=1)
SELECT quarter,employee_rank,employee_id,merchandise_value,product_id AS top_product_id,
       product_value AS top_product_value,ROUND(100.0*product_value/NULLIF(merchandise_value,0),2) AS top_share_pct
FROM leaders WHERE employee_rank<=3 ORDER BY quarter,employee_rank;$ent_045_reference_sql$,
$ent_045_difficulty$hard$ent_045_difficulty$,
$ent_045_primary_skill_group$S5$ent_045_primary_skill_group$,
$ent_045_primary_business_domain$Sales & Orders$ent_045_primary_business_domain$,
$ent_045_skills$[
  "window"
]$ent_045_skills$::jsonb,
NULL,
$ent_045_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Trong đơn delivered được gán nhân viên, tổng line_total theo quý order_date, nhân viên và sản phẩm; chọn sản phẩm có tổng lớn nhất mỗi nhân viên-quý (hòa chọn product_id nhỏ). Tính tổng line_total của nhân viên-quý rồi lấy tối đa 3 nhân viên mỗi quý theo tổng giảm, employee_id tăng. Trả sản phẩm dẫn đầu và tỷ trọng đóng góp của nó. Đây là giá trị hàng theo dòng, không gồm shipping_fee, không trừ refund hoặc trả hàng vật lý, không phải tiền ròng.",
  "output_grain": "Một nhân viên được chọn mỗi quý",
  "tables_used": [
    "orders",
    "order_items"
  ],
  "difficulty_reason": "Xếp hạng ở hai grain khác nhau: sản phẩm trong nhân viên-quý và nhân viên trong quý; tổng nhân viên phải bao gồm cả sản phẩm không thắng. Tie và mẫu số cần xác định riêng.",
  "order_by": "quarter tăng, employee_rank tăng",
  "edge_cases": "Tổng bằng 0 thì tỷ trọng NULL; phần trăm làm tròn 2 chữ số; không giữ thêm đồng hạng.",
  "time_basis": "Quý order_date; quarter là ngày đầu quý.",
  "result_limit": "Tối đa 3 nhân viên mỗi quý.",
  "logic_signature": {
    "goal": "Nhân viên dẫn đầu quý và sản phẩm đóng góp lớn nhất",
    "central_table": "orders",
    "grain": "Một nhân viên được chọn mỗi quý",
    "transformation": "quarter employee product aggregate product leader employee totals top three share",
    "predicate": "Trong đơn delivered được gán nhân viên, tổng line_total theo quý order_date, nhân viên và sản phẩm; chọn sản phẩm có tổng lớn nhất mỗi nhân viên-quý (hòa chọn product_id nhỏ). Tính tổng line_total của nhân viên-quý rồi lấy tối đa 3 nhân viên mỗi quý theo tổng giảm, employee_id tăng. Trả sản phẩm dẫn đầu và tỷ trọng đóng góp của nó. Đây là giá trị hàng theo dòng, không gồm shipping_fee, không trừ refund hoặc trả hàng vật lý, không phải tiền ròng.",
    "edge_cases": "Tổng bằng 0 thì tỷ trọng NULL; phần trăm làm tròn 2 chữ số; không giữ thêm đồng hạng."
  },
  "output_columns": [
    {
      "name": "quarter",
      "meaning": "Ngày đầu quý"
    },
    {
      "name": "employee_rank",
      "meaning": "Vị trí nhân viên trong quý"
    },
    {
      "name": "employee_id",
      "meaning": "Mã nhân viên"
    },
    {
      "name": "merchandise_value",
      "meaning": "Tổng line_total, không gồm shipping_fee hoặc trừ refund, VND"
    },
    {
      "name": "top_product_id",
      "meaning": "Mã sản phẩm đóng góp lớn nhất theo quy tắc chọn trong đề"
    },
    {
      "name": "top_product_value",
      "meaning": "Tổng line_total của sản phẩm đứng đầu, VND"
    },
    {
      "name": "top_share_pct",
      "meaning": "Tỷ trọng phần trăm sản phẩm đứng đầu"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_045_metadata$::jsonb,
$ent_045_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 21,
  "runtime_ms": 10.361,
  "column_types": [
    {
      "name": "quarter",
      "postgres_type": "date"
    },
    {
      "name": "employee_rank",
      "postgres_type": "bigint"
    },
    {
      "name": "employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "merchandise_value",
      "postgres_type": "numeric"
    },
    {
      "name": "top_product_id",
      "postgres_type": "integer"
    },
    {
      "name": "top_product_value",
      "postgres_type": "numeric"
    },
    {
      "name": "top_share_pct",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "quarter": "2025-01-01",
        "employee_id": 99,
        "employee_rank": 1,
        "top_share_pct": "32.07",
        "top_product_id": 196,
        "merchandise_value": "10800877.68",
        "top_product_value": "3463794.22"
      },
      {
        "quarter": "2025-01-01",
        "employee_id": 89,
        "employee_rank": 2,
        "top_share_pct": "65.21",
        "top_product_id": 182,
        "merchandise_value": "6580890.05",
        "top_product_value": "4291112.15"
      },
      {
        "quarter": "2025-01-01",
        "employee_id": 5,
        "employee_rank": 3,
        "top_share_pct": "33.84",
        "top_product_id": 70,
        "merchandise_value": "6135430.64",
        "top_product_value": "2076305.43"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "order_items",
    "orders"
  ],
  "process_wall_ms": 186.181,
  "oracle_row_count": 21,
  "result_sha256": "e65a1cc0c6ba153883141f45447826d6126cd316c920380b050da002952d49cf",
  "oracle_sha256": "e65a1cc0c6ba153883141f45447826d6126cd316c920380b050da002952d49cf",
  "repeat_runtime_ms": 11.993,
  "repeat_result_sha256": "e65a1cc0c6ba153883141f45447826d6126cd316c920380b050da002952d49cf",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Xếp hạng ở hai grain khác nhau: sản phẩm trong nhân viên-quý và nhân viên trong quý; tổng nhân viên phải bao gồm cả sản phẩm không thắng. Tie và mẫu số cần xác định riêng.",
    "primary_skill_group": "S5"
  }
}$ent_045_validation$::jsonb
);

-- ENT-046
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_046_question_id$ENT-046$ent_046_question_id$,
$ent_046_world_id$enterprise_v1$ent_046_world_id$,
$ent_046_title$Chuỗi giảm tồn liên tiếp dưới ngưỡng 50 đơn vị$ent_046_title$,
$ent_046_question_text$Xét tháng 2025-03 đến 2026-09 cho mỗi cặp sản phẩm-kho có giao dịch. Tồn cuối tháng là tổng mọi quantity_change trước đầu tháng tiếp theo, kể cả giao dịch trước kỳ. Tháng đủ điều kiện khi tồn cuối < tồn đầu và tồn cuối <=50 đơn vị. Với mỗi cặp có tháng đủ điều kiện, tìm chuỗi tháng lịch đủ điều kiện liên tục dài nhất; hòa chọn chuỗi bắt đầu sớm hơn. Trả đầu/cuối chuỗi, số tháng và tổng số đơn vị giảm. Ngưỡng 50 là tham số phân tích, không phải Business Rule.
Cột kết quả theo thứ tự: product_id, warehouse_id, start_month, end_month, streak_months, depleted_units.
Sắp xếp: product_id tăng, warehouse_id tăng.
Quy tắc biên: Không có giao dịch trước kỳ thì tồn đầu=0; không bỏ tháng trống; bỏ cặp không có tháng giảm.
Thời gian: transaction_date; kỳ [2025-03-01,2026-10-01).
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_046_question_text$,
$ent_046_reference_sql$WITH pairs AS (
 SELECT DISTINCT product_id,warehouse_id FROM inventory_transactions), calendar AS (
 SELECT GENERATE_SERIES(TIMESTAMP '2025-03-01',TIMESTAMP '2026-09-01',INTERVAL '1 month')::date AS month),
opening AS (
 SELECT product_id,warehouse_id,SUM(quantity_change) AS opening_stock FROM inventory_transactions
 WHERE transaction_date<TIMESTAMP '2025-03-01' GROUP BY 1,2), movements AS (
 SELECT product_id,warehouse_id,DATE_TRUNC('month',transaction_date)::date AS month,SUM(quantity_change) AS delta
 FROM inventory_transactions WHERE transaction_date>=TIMESTAMP '2025-03-01' AND transaction_date<TIMESTAMP '2026-10-01'
 GROUP BY 1,2,3), monthly AS (
 SELECT p.product_id,p.warehouse_id,c.month,COALESCE(m.delta,0) AS delta,
 COALESCE(o.opening_stock,0)+SUM(COALESCE(m.delta,0)) OVER (
 PARTITION BY p.product_id,p.warehouse_id ORDER BY c.month ROWS UNBOUNDED PRECEDING) AS closing_stock
 FROM pairs p CROSS JOIN calendar c LEFT JOIN movements m
 ON m.product_id=p.product_id AND m.warehouse_id=p.warehouse_id AND m.month=c.month
 LEFT JOIN opening o ON o.product_id=p.product_id AND o.warehouse_id=p.warehouse_id), eligible AS (
 SELECT *,EXTRACT(YEAR FROM month)::int*12+EXTRACT(MONTH FROM month)::int
 -ROW_NUMBER() OVER (PARTITION BY product_id,warehouse_id ORDER BY month) AS island
 FROM monthly WHERE delta<0 AND closing_stock<=50), streaks AS (
 SELECT product_id,warehouse_id,MIN(month) AS start_month,MAX(month) AS end_month,
 COUNT(*) AS streak_months,-SUM(delta) AS depleted_units FROM eligible GROUP BY product_id,warehouse_id,island), picked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY product_id,warehouse_id ORDER BY streak_months DESC,start_month) AS pos FROM streaks)
SELECT product_id,warehouse_id,start_month,end_month,streak_months,depleted_units FROM picked WHERE pos=1
ORDER BY product_id,warehouse_id;$ent_046_reference_sql$,
$ent_046_difficulty$hard$ent_046_difficulty$,
$ent_046_primary_skill_group$S6$ent_046_primary_skill_group$,
$ent_046_primary_business_domain$Product & Inventory$ent_046_primary_business_domain$,
$ent_046_skills$[
  "calendar",
  "window"
]$ent_046_skills$::jsonb,
NULL,
$ent_046_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Xét tháng 2025-03 đến 2026-09 cho mỗi cặp sản phẩm-kho có giao dịch. Tồn cuối tháng là tổng mọi quantity_change trước đầu tháng tiếp theo, kể cả giao dịch trước kỳ. Tháng đủ điều kiện khi tồn cuối < tồn đầu và tồn cuối <=50 đơn vị. Với mỗi cặp có tháng đủ điều kiện, tìm chuỗi tháng lịch đủ điều kiện liên tục dài nhất; hòa chọn chuỗi bắt đầu sớm hơn. Trả đầu/cuối chuỗi, số tháng và tổng số đơn vị giảm. Ngưỡng 50 là tham số phân tích, không phải Business Rule.",
  "output_grain": "Một cặp sản phẩm-kho có chuỗi giảm",
  "tables_used": [
    "inventory_transactions"
  ],
  "difficulty_reason": "Cần dựng lịch đầy đủ, đưa tồn trước kỳ vào tích lũy, so sánh hai đầu tháng và gom đảo giảm liên tiếp. Tháng trống phải cắt chuỗi giảm.",
  "order_by": "product_id tăng, warehouse_id tăng",
  "edge_cases": "Không có giao dịch trước kỳ thì tồn đầu=0; không bỏ tháng trống; bỏ cặp không có tháng giảm.",
  "time_basis": "transaction_date; kỳ [2025-03-01,2026-10-01).",
  "result_limit": null,
  "logic_signature": {
    "goal": "Chuỗi giảm tồn liên tiếp dưới ngưỡng 50 đơn vị",
    "central_table": "inventory_transactions",
    "grain": "Một cặp sản phẩm-kho có chuỗi giảm",
    "transformation": "pair calendar historical opening closing stock low threshold negative delta islands longest depletion",
    "predicate": "Xét tháng 2025-03 đến 2026-09 cho mỗi cặp sản phẩm-kho có giao dịch. Tồn cuối tháng là tổng mọi quantity_change trước đầu tháng tiếp theo, kể cả giao dịch trước kỳ. Tháng đủ điều kiện khi tồn cuối < tồn đầu và tồn cuối <=50 đơn vị. Với mỗi cặp có tháng đủ điều kiện, tìm chuỗi tháng lịch đủ điều kiện liên tục dài nhất; hòa chọn chuỗi bắt đầu sớm hơn. Trả đầu/cuối chuỗi, số tháng và tổng số đơn vị giảm. Ngưỡng 50 là tham số phân tích, không phải Business Rule.",
    "edge_cases": "Không có giao dịch trước kỳ thì tồn đầu=0; không bỏ tháng trống; bỏ cặp không có tháng giảm."
  },
  "output_columns": [
    {
      "name": "product_id",
      "meaning": "Mã sản phẩm"
    },
    {
      "name": "warehouse_id",
      "meaning": "Mã kho"
    },
    {
      "name": "start_month",
      "meaning": "Ngày đầu tháng bắt đầu đoạn"
    },
    {
      "name": "end_month",
      "meaning": "Ngày đầu tháng kết thúc đoạn"
    },
    {
      "name": "streak_months",
      "meaning": "Số tháng lịch liên tiếp trong đoạn"
    },
    {
      "name": "depleted_units",
      "meaning": "Tổng giảm đơn vị trong đoạn được chọn"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_046_metadata$::jsonb,
$ent_046_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 267,
  "runtime_ms": 38.904,
  "column_types": [
    {
      "name": "product_id",
      "postgres_type": "integer"
    },
    {
      "name": "warehouse_id",
      "postgres_type": "integer"
    },
    {
      "name": "start_month",
      "postgres_type": "date"
    },
    {
      "name": "end_month",
      "postgres_type": "date"
    },
    {
      "name": "streak_months",
      "postgres_type": "bigint"
    },
    {
      "name": "depleted_units",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "end_month": "2026-03-01",
        "product_id": 1,
        "start_month": "2026-03-01",
        "warehouse_id": 6,
        "streak_months": 1,
        "depleted_units": 1
      },
      {
        "end_month": "2025-04-01",
        "product_id": 2,
        "start_month": "2025-04-01",
        "warehouse_id": 2,
        "streak_months": 1,
        "depleted_units": 2
      },
      {
        "end_month": "2025-09-01",
        "product_id": 3,
        "start_month": "2025-09-01",
        "warehouse_id": 3,
        "streak_months": 1,
        "depleted_units": 1
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "inventory_transactions"
  ],
  "process_wall_ms": 106.573,
  "oracle_row_count": 267,
  "result_sha256": "cb1c92718364dbe70bd42c7d2038916183c70a4469c574e6d4e8997e8746882e",
  "oracle_sha256": "cb1c92718364dbe70bd42c7d2038916183c70a4469c574e6d4e8997e8746882e",
  "repeat_runtime_ms": 39.738,
  "repeat_result_sha256": "cb1c92718364dbe70bd42c7d2038916183c70a4469c574e6d4e8997e8746882e",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần dựng lịch đầy đủ, đưa tồn trước kỳ vào tích lũy, so sánh hai đầu tháng và gom đảo giảm liên tiếp. Tháng trống phải cắt chuỗi giảm.",
    "primary_skill_group": "S6"
  }
}$ent_046_validation$::jsonb
);

-- ENT-047
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_047_question_id$ENT-047$ent_047_question_id$,
$ent_047_world_id$enterprise_v1$ent_047_world_id$,
$ent_047_title$Quy mô cây nhân sự dưới trưởng phòng$ent_047_title$,
$ent_047_question_text$Với mỗi phòng ban, bắt đầu từ manager_employee_id được chỉ định và duyệt mọi hậu duệ qua employees.manager_id, không giới hạn phòng của hậu duệ. Trả số hậu duệ (không gồm gốc), độ sâu lớn nhất với con trực tiếp ở độ sâu 1, và tổng current_salary của hậu duệ. Không có gốc hoặc không có con thì các số bằng 0.
Cột kết quả theo thứ tự: department_id, root_manager_id, descendant_count, max_depth, descendant_payroll.
Sắp xếp: department_id tăng.
Quy tắc biên: Không lọc status; đường đi dùng mảng ID chống chu trình; số liệu không gồm trưởng phòng gốc.
Thời gian: Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_047_question_text$,
$ent_047_reference_sql$WITH RECURSIVE tree AS (
 SELECT d.department_id,d.manager_employee_id AS root_manager_id,e.employee_id,0 AS depth,
        ARRAY[e.employee_id] AS path,e.current_salary
 FROM departments d JOIN employees e ON e.employee_id=d.manager_employee_id
 UNION ALL
 SELECT t.department_id,t.root_manager_id,e.employee_id,t.depth+1,t.path||e.employee_id,e.current_salary
 FROM tree t JOIN employees e ON e.manager_id=t.employee_id WHERE NOT e.employee_id=ANY(t.path))
SELECT d.department_id,d.manager_employee_id AS root_manager_id,
       COUNT(t.employee_id) FILTER (WHERE t.depth>0) AS descendant_count,
       COALESCE(MAX(t.depth),0) AS max_depth,
       COALESCE(SUM(t.current_salary) FILTER (WHERE t.depth>0),0) AS descendant_payroll
FROM departments d LEFT JOIN tree t ON t.department_id=d.department_id
GROUP BY d.department_id,d.manager_employee_id ORDER BY d.department_id;$ent_047_reference_sql$,
$ent_047_difficulty$hard$ent_047_difficulty$,
$ent_047_primary_skill_group$S6$ent_047_primary_skill_group$,
$ent_047_primary_business_domain$Human Resources$ent_047_primary_business_domain$,
$ent_047_skills$[
  "conditional_aggregation",
  "recursive_hierarchy"
]$ent_047_skills$::jsonb,
NULL,
$ent_047_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Với mỗi phòng ban, bắt đầu từ manager_employee_id được chỉ định và duyệt mọi hậu duệ qua employees.manager_id, không giới hạn phòng của hậu duệ. Trả số hậu duệ (không gồm gốc), độ sâu lớn nhất với con trực tiếp ở độ sâu 1, và tổng current_salary của hậu duệ. Không có gốc hoặc không có con thì các số bằng 0.",
  "output_grain": "Một phòng ban",
  "tables_used": [
    "departments",
    "employees"
  ],
  "difficulty_reason": "Cần đệ quy nhiều cấp, chống lặp đường đi, loại gốc khỏi thống kê và giữ phòng chưa có cây. SELF JOIN một cấp không giải được.",
  "order_by": "department_id tăng",
  "edge_cases": "Không lọc status; đường đi dùng mảng ID chống chu trình; số liệu không gồm trưởng phòng gốc.",
  "time_basis": "Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Quy mô cây nhân sự dưới trưởng phòng",
    "central_table": "departments",
    "grain": "Một phòng ban",
    "transformation": "designated manager recursive descendants depth payroll cycle guard",
    "predicate": "Với mỗi phòng ban, bắt đầu từ manager_employee_id được chỉ định và duyệt mọi hậu duệ qua employees.manager_id, không giới hạn phòng của hậu duệ. Trả số hậu duệ (không gồm gốc), độ sâu lớn nhất với con trực tiếp ở độ sâu 1, và tổng current_salary của hậu duệ. Không có gốc hoặc không có con thì các số bằng 0.",
    "edge_cases": "Không lọc status; đường đi dùng mảng ID chống chu trình; số liệu không gồm trưởng phòng gốc."
  },
  "output_columns": [
    {
      "name": "department_id",
      "meaning": "Mã phòng hiện tại"
    },
    {
      "name": "root_manager_id",
      "meaning": "Mã trưởng phòng gốc của cây"
    },
    {
      "name": "descendant_count",
      "meaning": "Số hậu duệ không gồm gốc"
    },
    {
      "name": "max_depth",
      "meaning": "Độ sâu lớn nhất, con trực tiếp có độ sâu 1"
    },
    {
      "name": "descendant_payroll",
      "meaning": "Tổng lương hiện tại của hậu duệ, không gồm gốc, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_047_metadata$::jsonb,
$ent_047_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 5.356,
  "column_types": [
    {
      "name": "department_id",
      "postgres_type": "integer"
    },
    {
      "name": "root_manager_id",
      "postgres_type": "integer"
    },
    {
      "name": "descendant_count",
      "postgres_type": "bigint"
    },
    {
      "name": "max_depth",
      "postgres_type": "integer"
    },
    {
      "name": "descendant_payroll",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "max_depth": 2,
        "department_id": 1,
        "root_manager_id": 1,
        "descendant_count": 12,
        "descendant_payroll": "319000000.00"
      },
      {
        "max_depth": 2,
        "department_id": 2,
        "root_manager_id": 2,
        "descendant_count": 12,
        "descendant_payroll": "301000000.00"
      },
      {
        "max_depth": 2,
        "department_id": 3,
        "root_manager_id": 3,
        "descendant_count": 12,
        "descendant_payroll": "308000000.00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "departments",
    "employees"
  ],
  "process_wall_ms": 80.377,
  "oracle_row_count": 8,
  "result_sha256": "09a2841f270ae060de39722a7717a5b9435256d740e0754e96ad7c925c232a97",
  "oracle_sha256": "09a2841f270ae060de39722a7717a5b9435256d740e0754e96ad7c925c232a97",
  "repeat_runtime_ms": 5.329,
  "repeat_result_sha256": "09a2841f270ae060de39722a7717a5b9435256d740e0754e96ad7c925c232a97",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần đệ quy nhiều cấp, chống lặp đường đi, loại gốc khỏi thống kê và giữ phòng chưa có cây. SELF JOIN một cấp không giải được.",
    "primary_skill_group": "S6"
  }
}$ent_047_validation$::jsonb
);

-- ENT-048
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_048_question_id$ENT-048$ent_048_question_id$,
$ent_048_world_id$enterprise_v1$ent_048_world_id$,
$ent_048_title$Mức lương tháng bình quân có bằng chứng trong năm 2025$ent_048_title$,
$ent_048_question_text$Theo phòng hiện tại, xét từng nhân viên từ max(hire_date,2025-01-01) đến hết 2025-12-31; ngày trước tuyển không tính. Mỗi salary_history.salary áp dụng từ effective_date đến trước mốc kế tiếp. Tính số ngày-nhân viên có mức lương lịch sử xác định, số ngày-nhân viên chưa xác định, và tổng (salary * số ngày áp dụng trong 2025) / 365 làm mức lương tháng bình quân quy đổi trên phần có bằng chứng. Đây là chỉ số lập ngân sách, không phải lương đã trả; không dùng current_salary để lấp giai đoạn thiếu.
Cột kết quả theo thứ tự: department_id, eligible_employee_days, known_salary_days, unknown_salary_days, evidenced_monthly_payroll.
Sắp xếp: department_id tăng.
Quy tắc biên: Không có lịch sử thì known=0 và unknown=mọi ngày eligible; chỉ số lương bằng 0 nếu không có phần được ghi nhận; ngày kết thúc loại trừ.
Thời gian: Năm 2025 có 365 ngày; hiệu lực [effective_date,next_effective_date).
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_048_question_text$,
$ent_048_reference_sql$WITH intervals AS (
 SELECT employee_id,salary,effective_date,
 LEAD(effective_date,1,DATE '2026-01-01') OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS next_date
 FROM salary_history), clipped AS (
 SELECT e.employee_id,e.department_id,s.salary,
 GREATEST(LEAST(s.next_date,DATE '2026-01-01')-GREATEST(s.effective_date,e.hire_date,DATE '2025-01-01'),0) AS days
 FROM employees e JOIN intervals s ON s.employee_id=e.employee_id WHERE e.hire_date<DATE '2026-01-01'),
known AS (
 SELECT employee_id,SUM(days) AS known_days,SUM(salary*days) AS weighted_salary FROM clipped GROUP BY employee_id),
eligible AS (
 SELECT e.department_id,DATE '2026-01-01'-GREATEST(e.hire_date,DATE '2025-01-01') AS eligible_days,
 COALESCE(k.known_days,0) AS known_days,COALESCE(k.weighted_salary,0) AS weighted_salary
 FROM employees e LEFT JOIN known k USING(employee_id) WHERE e.hire_date<DATE '2026-01-01')
SELECT department_id,SUM(eligible_days) AS eligible_employee_days,SUM(known_days) AS known_salary_days,
       SUM(eligible_days-known_days) AS unknown_salary_days,
       ROUND(SUM(weighted_salary)/365.0,2) AS evidenced_monthly_payroll
FROM eligible GROUP BY department_id ORDER BY department_id;$ent_048_reference_sql$,
$ent_048_difficulty$hard$ent_048_difficulty$,
$ent_048_primary_skill_group$S6$ent_048_primary_skill_group$,
$ent_048_primary_business_domain$Finance$ent_048_primary_business_domain$,
$ent_048_skills$[
  "window",
  "temporal_intervals"
]$ent_048_skills$::jsonb,
NULL,
$ent_048_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Theo phòng hiện tại, xét từng nhân viên từ max(hire_date,2025-01-01) đến hết 2025-12-31; ngày trước tuyển không tính. Mỗi salary_history.salary áp dụng từ effective_date đến trước mốc kế tiếp. Tính số ngày-nhân viên có mức lương lịch sử xác định, số ngày-nhân viên chưa xác định, và tổng (salary * số ngày áp dụng trong 2025) / 365 làm mức lương tháng bình quân quy đổi trên phần có bằng chứng. Đây là chỉ số lập ngân sách, không phải lương đã trả; không dùng current_salary để lấp giai đoạn thiếu.",
  "output_grain": "Một phòng có ít nhất một nhân viên được tuyển trước hết 2025",
  "tables_used": [
    "employees",
    "salary_history"
  ],
  "difficulty_reason": "Cần dựng khoảng hiệu lực, cắt theo ngày tuyển và năm, cộng mức lương nhân số ngày rồi đối chiếu độ phủ. Lương hiện tại không xác định được quá khứ bị thiếu.",
  "order_by": "department_id tăng",
  "edge_cases": "Không có lịch sử thì known=0 và unknown=mọi ngày eligible; chỉ số lương bằng 0 nếu không có phần được ghi nhận; ngày kết thúc loại trừ.",
  "time_basis": "Năm 2025 có 365 ngày; hiệu lực [effective_date,next_effective_date).",
  "result_limit": null,
  "logic_signature": {
    "goal": "Mức lương tháng bình quân có bằng chứng trong năm 2025",
    "central_table": "employees",
    "grain": "Một phòng có ít nhất một nhân viên được tuyển trước hết 2025",
    "transformation": "salary effective intervals clip employment year weighted salary days missing coverage",
    "predicate": "Theo phòng hiện tại, xét từng nhân viên từ max(hire_date,2025-01-01) đến hết 2025-12-31; ngày trước tuyển không tính. Mỗi salary_history.salary áp dụng từ effective_date đến trước mốc kế tiếp. Tính số ngày-nhân viên có mức lương lịch sử xác định, số ngày-nhân viên chưa xác định, và tổng (salary * số ngày áp dụng trong 2025) / 365 làm mức lương tháng bình quân quy đổi trên phần có bằng chứng. Đây là chỉ số lập ngân sách, không phải lương đã trả; không dùng current_salary để lấp giai đoạn thiếu.",
    "edge_cases": "Không có lịch sử thì known=0 và unknown=mọi ngày eligible; chỉ số lương bằng 0 nếu không có phần được ghi nhận; ngày kết thúc loại trừ."
  },
  "output_columns": [
    {
      "name": "department_id",
      "meaning": "Mã phòng hiện tại"
    },
    {
      "name": "eligible_employee_days",
      "meaning": "Tổng ngày-nhân viên sau ngày tuyển trong năm"
    },
    {
      "name": "known_salary_days",
      "meaning": "Tổng ngày-nhân viên có mức lương lịch sử xác định"
    },
    {
      "name": "unknown_salary_days",
      "meaning": "Tổng ngày-nhân viên chưa biết mức lương lịch sử"
    },
    {
      "name": "evidenced_monthly_payroll",
      "meaning": "Tổng salary*ngày có bằng chứng chia 365; chỉ số ngân sách, VND"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_048_metadata$::jsonb,
$ent_048_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 8,
  "runtime_ms": 7.714,
  "column_types": [
    {
      "name": "department_id",
      "postgres_type": "integer"
    },
    {
      "name": "eligible_employee_days",
      "postgres_type": "bigint"
    },
    {
      "name": "known_salary_days",
      "postgres_type": "numeric"
    },
    {
      "name": "unknown_salary_days",
      "postgres_type": "numeric"
    },
    {
      "name": "evidenced_monthly_payroll",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "department_id": 1,
        "known_salary_days": 4745,
        "unknown_salary_days": 0,
        "eligible_employee_days": 4745,
        "evidenced_monthly_payroll": "389062356.16"
      },
      {
        "department_id": 2,
        "known_salary_days": 3276,
        "unknown_salary_days": 1469,
        "eligible_employee_days": 4745,
        "evidenced_monthly_payroll": "271094575.34"
      },
      {
        "department_id": 3,
        "known_salary_days": 4745,
        "unknown_salary_days": 0,
        "eligible_employee_days": 4745,
        "evidenced_monthly_payroll": "370860602.74"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "employees",
    "salary_history"
  ],
  "process_wall_ms": 80.52,
  "oracle_row_count": 8,
  "result_sha256": "7fc3abc4cbbd55d2ff4df63acdfc939494560d48501825338396b2464d7881d2",
  "oracle_sha256": "7fc3abc4cbbd55d2ff4df63acdfc939494560d48501825338396b2464d7881d2",
  "repeat_runtime_ms": 6.784,
  "repeat_result_sha256": "7fc3abc4cbbd55d2ff4df63acdfc939494560d48501825338396b2464d7881d2",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần dựng khoảng hiệu lực, cắt theo ngày tuyển và năm, cộng mức lương nhân số ngày rồi đối chiếu độ phủ. Lương hiện tại không xác định được quá khứ bị thiếu.",
    "primary_skill_group": "S6"
  }
}$ent_048_validation$::jsonb
);

-- ENT-049
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_049_question_id$ENT-049$ent_049_question_id$,
$ent_049_world_id$enterprise_v1$ent_049_world_id$,
$ent_049_title$Nút thắt trạng thái phổ biến theo kho và quý$ent_049_title$,
$ent_049_question_text$Với đơn hiện tại delivered có warehouse_id không NULL, sắp history theo changed_at,history_id. Thời gian một trạng thái là từ sự kiện vào trạng thái đến sự kiện kế tiếp. Trong pending,processing,shipped, chọn trạng thái có thời gian dài nhất của mỗi đơn; hòa ưu tiên pending rồi processing rồi shipped. Nhóm theo warehouse_id và quý order_date; chọn trạng thái được nhiều đơn chọn nhất, hòa theo ưu tiên trên. Trả số đơn chọn trạng thái đó và số giờ trung bình của đoạn trạng thái trên những đơn đó.
Cột kết quả theo thứ tự: warehouse_id, quarter, bottleneck_status, selected_orders, avg_stage_hours.
Sắp xếp: warehouse_id tăng, quarter tăng.
Quy tắc biên: Không tính thời gian delivered vì không có sự kiện kết thúc; trung bình giờ làm tròn 2 chữ số.
Thời gian: Độ dài bằng changed_at; nhóm quý theo order_date.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_049_question_text$,
$ent_049_reference_sql$WITH episodes AS (
 SELECT o.order_id,o.warehouse_id,DATE_TRUNC('quarter',o.order_date)::date AS quarter,h.new_status,
 h.changed_at,LEAD(h.changed_at) OVER (PARTITION BY o.order_id ORDER BY h.changed_at,h.history_id) AS next_at
 FROM orders o JOIN order_status_history h ON h.order_id=o.order_id
 WHERE o.status='delivered' AND o.warehouse_id IS NOT NULL), stages AS (
 SELECT *,EXTRACT(EPOCH FROM next_at-changed_at)/3600 AS hours,
 CASE new_status WHEN 'pending' THEN 1 WHEN 'processing' THEN 2 WHEN 'shipped' THEN 3 END AS priority
 FROM episodes WHERE new_status IN ('pending','processing','shipped') AND next_at IS NOT NULL),
per_order AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY hours DESC,priority) AS pos FROM stages), totals AS (
 SELECT warehouse_id,quarter,new_status,priority,COUNT(*) AS selected_orders,AVG(hours) AS average_hours
 FROM per_order WHERE pos=1 GROUP BY 1,2,3,4), picked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY warehouse_id,quarter ORDER BY selected_orders DESC,priority) AS pos FROM totals)
SELECT warehouse_id,quarter,new_status AS bottleneck_status,selected_orders,ROUND(average_hours,2) AS avg_stage_hours
FROM picked WHERE pos=1 ORDER BY warehouse_id,quarter;$ent_049_reference_sql$,
$ent_049_difficulty$hard$ent_049_difficulty$,
$ent_049_primary_skill_group$S6$ent_049_primary_skill_group$,
$ent_049_primary_business_domain$Sales & Orders$ent_049_primary_business_domain$,
$ent_049_skills$[
  "conditional_aggregation",
  "window",
  "temporal_intervals"
]$ent_049_skills$::jsonb,
NULL,
$ent_049_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Với đơn hiện tại delivered có warehouse_id không NULL, sắp history theo changed_at,history_id. Thời gian một trạng thái là từ sự kiện vào trạng thái đến sự kiện kế tiếp. Trong pending,processing,shipped, chọn trạng thái có thời gian dài nhất của mỗi đơn; hòa ưu tiên pending rồi processing rồi shipped. Nhóm theo warehouse_id và quý order_date; chọn trạng thái được nhiều đơn chọn nhất, hòa theo ưu tiên trên. Trả số đơn chọn trạng thái đó và số giờ trung bình của đoạn trạng thái trên những đơn đó.",
  "output_grain": "Một kho-quý có đơn delivered",
  "tables_used": [
    "orders",
    "order_status_history"
  ],
  "difficulty_reason": "Phải tái dựng đoạn lịch sử, chọn cực đại từng đơn rồi chọn mode ở grain kho-quý. Hai tầng lựa chọn có tie riêng và không được trộn thời gian của trạng thái khác.",
  "order_by": "warehouse_id tăng, quarter tăng",
  "edge_cases": "Không tính thời gian delivered vì không có sự kiện kết thúc; trung bình giờ làm tròn 2 chữ số.",
  "time_basis": "Độ dài bằng changed_at; nhóm quý theo order_date.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Nút thắt trạng thái phổ biến theo kho và quý",
    "central_table": "orders",
    "grain": "Một kho-quý có đơn delivered",
    "transformation": "status lead intervals per order bottleneck then warehouse quarter modal bottleneck",
    "predicate": "Với đơn hiện tại delivered có warehouse_id không NULL, sắp history theo changed_at,history_id. Thời gian một trạng thái là từ sự kiện vào trạng thái đến sự kiện kế tiếp. Trong pending,processing,shipped, chọn trạng thái có thời gian dài nhất của mỗi đơn; hòa ưu tiên pending rồi processing rồi shipped. Nhóm theo warehouse_id và quý order_date; chọn trạng thái được nhiều đơn chọn nhất, hòa theo ưu tiên trên. Trả số đơn chọn trạng thái đó và số giờ trung bình của đoạn trạng thái trên những đơn đó.",
    "edge_cases": "Không tính thời gian delivered vì không có sự kiện kết thúc; trung bình giờ làm tròn 2 chữ số."
  },
  "output_columns": [
    {
      "name": "warehouse_id",
      "meaning": "Mã kho"
    },
    {
      "name": "quarter",
      "meaning": "Ngày đầu quý"
    },
    {
      "name": "bottleneck_status",
      "meaning": "Trạng thái thắng hai tầng chọn theo đề"
    },
    {
      "name": "selected_orders",
      "meaning": "Số đơn chọn trạng thái thắng"
    },
    {
      "name": "avg_stage_hours",
      "meaning": "Giờ trung bình đoạn trạng thái thắng của các đơn chọn nó"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_049_metadata$::jsonb,
$ent_049_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 55,
  "runtime_ms": 10.92,
  "column_types": [
    {
      "name": "warehouse_id",
      "postgres_type": "integer"
    },
    {
      "name": "quarter",
      "postgres_type": "date"
    },
    {
      "name": "bottleneck_status",
      "postgres_type": "character varying(30)"
    },
    {
      "name": "selected_orders",
      "postgres_type": "bigint"
    },
    {
      "name": "avg_stage_hours",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "quarter": "2025-01-01",
        "warehouse_id": 1,
        "avg_stage_hours": "49.00",
        "selected_orders": 1,
        "bottleneck_status": "processing"
      },
      {
        "quarter": "2025-04-01",
        "warehouse_id": 1,
        "avg_stage_hours": "87.00",
        "selected_orders": 12,
        "bottleneck_status": "shipped"
      },
      {
        "quarter": "2025-07-01",
        "warehouse_id": 1,
        "avg_stage_hours": "85.00",
        "selected_orders": 2,
        "bottleneck_status": "processing"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "order_status_history",
    "orders"
  ],
  "process_wall_ms": 77.949,
  "oracle_row_count": 55,
  "result_sha256": "2bf38978aaa6c9802610d7d2e4c868dc40ceebad92a9377a69113a8b2a5bca20",
  "oracle_sha256": "2bf38978aaa6c9802610d7d2e4c868dc40ceebad92a9377a69113a8b2a5bca20",
  "repeat_runtime_ms": 12.603,
  "repeat_result_sha256": "2bf38978aaa6c9802610d7d2e4c868dc40ceebad92a9377a69113a8b2a5bca20",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Phải tái dựng đoạn lịch sử, chọn cực đại từng đơn rồi chọn mode ở grain kho-quý. Hai tầng lựa chọn có tie riêng và không được trộn thời gian của trạng thái khác.",
    "primary_skill_group": "S6"
  }
}$ent_049_validation$::jsonb
);

-- ENT-050
INSERT INTO core.source_questions (question_id,world_id,title,question_text,reference_sql,difficulty,primary_skill_group,primary_business_domain,skills,depth,metadata,validation) VALUES (
$ent_050_question_id$ENT-050$ent_050_question_id$,
$ent_050_world_id$enterprise_v1$ent_050_world_id$,
$ent_050_title$Chuỗi tăng lương liên tiếp có mức tăng tổng cao nhất$ent_050_title$,
$ent_050_question_text$Theo từng nhân viên, sắp salary_history bằng effective_date,salary_history_id. Một chuỗi tăng là một đoạn tối đa gồm các mốc liên tiếp có salary sau > salary trước; mốc bằng hoặc giảm cắt chuỗi. Chỉ xét chuỗi có ít nhất 2 lần tăng. Chọn một chuỗi mỗi nhân viên theo tỷ lệ (lương cuối/lương đầu-1) giảm, số lần tăng giảm, ngày bắt đầu tăng. Trả ngày đầu (mốc trước lần tăng thứ nhất), ngày cuối, số lần tăng, lương đầu/cuối và tỷ lệ tăng phần trăm.
Cột kết quả theo thứ tự: employee_id, start_date, end_date, raise_count, start_salary, end_salary, growth_pct.
Sắp xếp: employee_id tăng.
Quy tắc biên: Mốc bằng/giảm cắt chuỗi; xếp bằng tỷ lệ chưa làm tròn, chỉ làm tròn growth_pct đầu ra 2 chữ số.
Thời gian: effective_date; salary_history_id phá hòa.
Mọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.$ent_050_question_text$,
$ent_050_reference_sql$WITH previous AS (
 SELECT *,LAG(salary) OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS previous_salary,
 LAG(effective_date) OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS previous_date
 FROM salary_history), numbered AS (
 SELECT *,SUM(CASE WHEN previous_salary IS NULL OR salary<=previous_salary THEN 1 ELSE 0 END)
 OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id ROWS UNBOUNDED PRECEDING) AS island
 FROM previous), streaks AS (
 SELECT employee_id,island,MIN(previous_date) AS start_date,MAX(effective_date) AS end_date,
 COUNT(*) AS raise_count,MIN(previous_salary) AS start_salary,MAX(salary) AS end_salary
 FROM numbered WHERE salary>previous_salary GROUP BY employee_id,island HAVING COUNT(*)>=2), ranked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY employee_id
 ORDER BY (end_salary/start_salary-1) DESC,raise_count DESC,start_date) AS pos FROM streaks)
SELECT employee_id,start_date,end_date,raise_count,start_salary,end_salary,
       ROUND(100.0*(end_salary/start_salary-1),2) AS growth_pct
FROM ranked WHERE pos=1 ORDER BY employee_id;$ent_050_reference_sql$,
$ent_050_difficulty$hard$ent_050_difficulty$,
$ent_050_primary_skill_group$S6$ent_050_primary_skill_group$,
$ent_050_primary_business_domain$Human Resources$ent_050_primary_business_domain$,
$ent_050_skills$[
  "conditional_aggregation",
  "window"
]$ent_050_skills$::jsonb,
NULL,
$ent_050_metadata${
  "taxonomy_version": "v1",
  "business_goal": "Theo từng nhân viên, sắp salary_history bằng effective_date,salary_history_id. Một chuỗi tăng là một đoạn tối đa gồm các mốc liên tiếp có salary sau > salary trước; mốc bằng hoặc giảm cắt chuỗi. Chỉ xét chuỗi có ít nhất 2 lần tăng. Chọn một chuỗi mỗi nhân viên theo tỷ lệ (lương cuối/lương đầu-1) giảm, số lần tăng giảm, ngày bắt đầu tăng. Trả ngày đầu (mốc trước lần tăng thứ nhất), ngày cuối, số lần tăng, lương đầu/cuối và tỷ lệ tăng phần trăm.",
  "output_grain": "Một nhân viên có chuỗi ít nhất hai lần tăng",
  "tables_used": [
    "salary_history"
  ],
  "difficulty_reason": "Cần phát hiện các cạnh tăng, giữ mốc tiền nhiệm ở đầu chuỗi, gom đoạn tối đa rồi so sánh tỷ lệ hai đầu. Tính từng LAG riêng lẻ không xác định được chuỗi tốt nhất.",
  "order_by": "employee_id tăng",
  "edge_cases": "Mốc bằng/giảm cắt chuỗi; xếp bằng tỷ lệ chưa làm tròn, chỉ làm tròn growth_pct đầu ra 2 chữ số.",
  "time_basis": "effective_date; salary_history_id phá hòa.",
  "result_limit": null,
  "logic_signature": {
    "goal": "Chuỗi tăng lương liên tiếp có mức tăng tổng cao nhất",
    "central_table": "salary_history",
    "grain": "Một nhân viên có chuỗi ít nhất hai lần tăng",
    "transformation": "adjacent salary raises maximal islands endpoint growth best streak",
    "predicate": "Theo từng nhân viên, sắp salary_history bằng effective_date,salary_history_id. Một chuỗi tăng là một đoạn tối đa gồm các mốc liên tiếp có salary sau > salary trước; mốc bằng hoặc giảm cắt chuỗi. Chỉ xét chuỗi có ít nhất 2 lần tăng. Chọn một chuỗi mỗi nhân viên theo tỷ lệ (lương cuối/lương đầu-1) giảm, số lần tăng giảm, ngày bắt đầu tăng. Trả ngày đầu (mốc trước lần tăng thứ nhất), ngày cuối, số lần tăng, lương đầu/cuối và tỷ lệ tăng phần trăm.",
    "edge_cases": "Mốc bằng/giảm cắt chuỗi; xếp bằng tỷ lệ chưa làm tròn, chỉ làm tròn growth_pct đầu ra 2 chữ số."
  },
  "output_columns": [
    {
      "name": "employee_id",
      "meaning": "Mã nhân viên"
    },
    {
      "name": "start_date",
      "meaning": "Ngày hiệu lực mốc lương đầu đoạn"
    },
    {
      "name": "end_date",
      "meaning": "Ngày hiệu lực mốc lương cuối đoạn"
    },
    {
      "name": "raise_count",
      "meaning": "Số cạnh tăng lương liên tiếp trong đoạn"
    },
    {
      "name": "start_salary",
      "meaning": "Mức lương đầu đoạn, VND"
    },
    {
      "name": "end_salary",
      "meaning": "Mức lương cuối đoạn, VND"
    },
    {
      "name": "growth_pct",
      "meaning": "Phần trăm tăng giữa hai đầu đoạn"
    }
  ],
  "money_unit": "VND",
  "ordering_required": true
}$ent_050_metadata$::jsonb,
$ent_050_validation${
  "status": "PASS",
  "sql_executed": true,
  "semantic_valid": true,
  "row_count": 33,
  "runtime_ms": 5.641,
  "column_types": [
    {
      "name": "employee_id",
      "postgres_type": "integer"
    },
    {
      "name": "start_date",
      "postgres_type": "date"
    },
    {
      "name": "end_date",
      "postgres_type": "date"
    },
    {
      "name": "raise_count",
      "postgres_type": "bigint"
    },
    {
      "name": "start_salary",
      "postgres_type": "numeric"
    },
    {
      "name": "end_salary",
      "postgres_type": "numeric"
    },
    {
      "name": "growth_pct",
      "postgres_type": "numeric"
    }
  ],
  "result_summary": {
    "sample_rows": [
      {
        "end_date": "2022-05-31",
        "end_salary": "77000000.00",
        "growth_pct": "19.05",
        "start_date": "2021-02-05",
        "employee_id": 2,
        "raise_count": 2,
        "start_salary": "64680000.00"
      },
      {
        "end_date": "2023-03-15",
        "end_salary": "82000000.00",
        "growth_pct": "19.05",
        "start_date": "2021-11-20",
        "employee_id": 5,
        "raise_count": 2,
        "start_salary": "68880000.00"
      },
      {
        "end_date": "2024-05-30",
        "end_salary": "77000000.00",
        "growth_pct": "19.05",
        "start_date": "2023-02-05",
        "employee_id": 8,
        "raise_count": 2,
        "start_salary": "64680000.00"
      }
    ],
    "sample_limit": 3
  },
  "error": null,
  "plan_relations": [
    "salary_history"
  ],
  "process_wall_ms": 76.748,
  "oracle_row_count": 33,
  "result_sha256": "ed7a29fc0289e8317dec0f986a6a2d5ad0e79a5b586fce8942a27a560063dde6",
  "oracle_sha256": "ed7a29fc0289e8317dec0f986a6a2d5ad0e79a5b586fce8942a27a560063dde6",
  "repeat_runtime_ms": 6.513,
  "repeat_result_sha256": "ed7a29fc0289e8317dec0f986a6a2d5ad0e79a5b586fce8942a27a560063dde6",
  "stable_on_repeat": true,
  "semantic_evidence": "Complete ordered result equals independent Python evaluator on actual base rows.",
  "taxonomy_review": {
    "decision": "MATCHES_BASELINE_V1",
    "reason": "Cần phát hiện các cạnh tăng, giữ mốc tiền nhiệm ở đầu chuỗi, gom đoạn tối đa rồi so sánh tỷ lệ hai đầu. Tính từng LAG riêng lẻ không xác định được chuỗi tốt nhất.",
    "primary_skill_group": "S6"
  }
}$ent_050_validation$::jsonb
);

COMMIT;

SELECT 'worlds' AS table_name,COUNT(*) AS row_count FROM core.worlds
UNION ALL SELECT 'skills',COUNT(*) FROM core.skills
UNION ALL SELECT 'templates',COUNT(*) FROM core.templates
UNION ALL SELECT 'source_questions',COUNT(*) FROM core.source_questions;
