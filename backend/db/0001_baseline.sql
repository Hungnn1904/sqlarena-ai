-- =====================================================================
-- SQLArena Application DB - phần "AI Pipeline & Question Management" (Hưng)
-- Dẫn xuất từ Design v7 (db/postgres_schema.sql); khác biệt được ghi trong
-- docs/DESIGN_DECISIONS.md. Do Alembic revision 0001 chạy; cũng chạy độc lập được trên DB trống.
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS draft;
CREATE SCHEMA IF NOT EXISTS live;

-- ============================ core ===========================
CREATE TABLE core.worlds (
  world_id             serial PRIMARY KEY,
  name                 varchar(50)  NOT NULL UNIQUE,
  display_name         varchar(150),
  schema_description   jsonb        NOT NULL,
  fk_relations         jsonb        NOT NULL DEFAULT '[]'::jsonb,
  business_rules       jsonb,
  planted_traps        jsonb,
  allowed_sql_features jsonb,
  dialect              varchar(20)  NOT NULL DEFAULT 'postgresql' CHECK (dialect = 'postgresql'),
  dataset_ref          varchar(100) NOT NULL,
  variant_count        int          NOT NULL DEFAULT 0 CHECK (variant_count >= 0),
  dataset_version      int          NOT NULL DEFAULT 1 CHECK (dataset_version >= 1),
  is_active            boolean      NOT NULL DEFAULT true,
  created_at           timestamptz  NOT NULL DEFAULT now(),
  updated_at           timestamptz
);

CREATE TABLE core.skills (
  skill_id        serial PRIMARY KEY,
  code            varchar(30)  NOT NULL UNIQUE,
  name            varchar(160) NOT NULL UNIQUE,
  category        varchar(50)  NOT NULL,
  base_difficulty smallint     NOT NULL CHECK (base_difficulty BETWEEN 1 AND 3),
  description     text,
  is_active       boolean      NOT NULL DEFAULT true
);

CREATE TABLE core.templates (
  template_id serial PRIMARY KEY,
  world_id    int          NOT NULL REFERENCES core.worlds (world_id),
  topic       varchar(100) NOT NULL,
  difficulty  smallint     NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
  pattern     text         NOT NULL,
  constraints jsonb,
  is_active   boolean      NOT NULL DEFAULT true,
  created_at  timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE core.prompt_templates (
  prompt_id  serial PRIMARY KEY,
  name       varchar(50) NOT NULL CHECK (name IN ('model_a', 'solve_b', 'checklist_b')),
  version    varchar(50) NOT NULL,
  content    text        NOT NULL,
  is_active  boolean     NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name, version)
);
CREATE UNIQUE INDEX prompt_templates_one_active_idx ON core.prompt_templates (name) WHERE is_active;

CREATE TABLE core.system_settings (
  key         varchar(100) PRIMARY KEY,
  value       jsonb        NOT NULL,
  description varchar(255),
  updated_at  timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE core.source_questions (
  source_id               serial PRIMARY KEY,
  code                    varchar(30)  NOT NULL UNIQUE,
  world_id                int          NOT NULL REFERENCES core.worlds (world_id),
  title                   text         NOT NULL,
  question_text           text         NOT NULL,
  reference_sql           text         NOT NULL,
  difficulty              smallint     NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
  primary_skill_id        int          NOT NULL REFERENCES core.skills (skill_id),
  primary_business_domain varchar(100) NOT NULL,
  skills                  jsonb        NOT NULL DEFAULT '[]'::jsonb,
  depth                   int          CHECK (depth IS NULL OR depth >= 0),
  metadata                jsonb        NOT NULL,
  validation              jsonb        NOT NULL,
  created_at              timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX source_questions_world_idx ON core.source_questions (world_id, difficulty);

-- ================ live: danh tính tối thiểu (dùng chung với module Auth) ================
CREATE TABLE IF NOT EXISTS live.roles (
  role_id     serial PRIMARY KEY,
  name        varchar(30) NOT NULL UNIQUE CHECK (name IN ('learner', 'admin')),
  description varchar(255)
);
CREATE TABLE IF NOT EXISTS live.users (
  user_id       serial PRIMARY KEY,
  role_id       int          NOT NULL REFERENCES live.roles (role_id),
  email         varchar(255) NOT NULL,
  username      varchar(50)  NOT NULL,
  password_hash varchar(255) NOT NULL,
  display_name  varchar(100),
  avatar_url    varchar(500),
  bio           text,
  status        varchar(20)  NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'locked')),
  created_at    timestamptz  NOT NULL DEFAULT now(),
  last_login_at timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_uq ON live.users (lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS users_username_uq ON live.users (lower(username));

-- ============================ draft ===========================
CREATE TABLE draft.generation_jobs (
  job_id           serial PRIMARY KEY,
  world_id         int         NOT NULL REFERENCES core.worlds (world_id),
  triggered_by     int         NOT NULL REFERENCES live.users (user_id),
  trigger_type     varchar(20) NOT NULL DEFAULT 'manual' CHECK (trigger_type = 'manual'),
  difficulty       smallint    NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
  skill_ids        int[]       NOT NULL,
  topic            varchar(100),
  requested_count  int         NOT NULL CHECK (requested_count > 0),
  created_count    int         NOT NULL DEFAULT 0,
  failed_count     int         NOT NULL DEFAULT 0,
  status           varchar(20) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'done', 'failed')),
  error_message    text,
  attempt_count    smallint    NOT NULL DEFAULT 0,
  idempotency_key  varchar(100),
  request_hash     varchar(64),
  locked_by        varchar(100),
  locked_at        timestamptz,
  lease_expires_at timestamptz,
  lease_version    bigint      NOT NULL DEFAULT 0,
  created_at       timestamptz NOT NULL DEFAULT now(),
  started_at       timestamptz,
  finished_at      timestamptz,
  CONSTRAINT job_counts_within_request CHECK (created_count + failed_count <= requested_count)
);
CREATE INDEX generation_jobs_queue_idx ON draft.generation_jobs (status, created_at);
CREATE INDEX generation_jobs_running_idx ON draft.generation_jobs (lease_expires_at) WHERE status = 'running';
CREATE UNIQUE INDEX generation_jobs_idempotency_uq ON draft.generation_jobs (triggered_by, idempotency_key) WHERE idempotency_key IS NOT NULL;
COMMENT ON COLUMN draft.generation_jobs.lease_version IS 'Fencing token tăng mỗi lần claim; completion chỉ ghi nếu worker còn giữ đúng token.';

CREATE TABLE draft.question_drafts (
  draft_id           serial PRIMARY KEY,
  world_id           int          NOT NULL REFERENCES core.worlds (world_id),
  template_id        int          REFERENCES core.templates (template_id),
  job_id             int          REFERENCES draft.generation_jobs (job_id),
  title              varchar(200) NOT NULL,
  question           text         NOT NULL,
  reference_sql      text,
  compare_mode       varchar(20)  CHECK (compare_mode IN ('ordered', 'unordered')),
  difficulty         smallint     NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
  skill_ids          int[]        NOT NULL,
  blueprint          jsonb        NOT NULL,
  tables_used        text[],
  traps              jsonb,
  parent_ids         int[],
  schema_text        text         NOT NULL DEFAULT '',
  schema_context     jsonb        NOT NULL DEFAULT '{}'::jsonb,
  validation_report  jsonb        NOT NULL DEFAULT '{}'::jsonb,
  status             varchar(20)  NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'reviewing', 'approved', 'rejected', 'needs_human')),
  status_reason      text,
  gen_model          varchar(100) NOT NULL,
  gen_prompt_version varchar(50)  NOT NULL,
  retry_count        smallint     NOT NULL DEFAULT 0,
  review_attempts    smallint     NOT NULL DEFAULT 0,
  locked_by          varchar(100),
  locked_at          timestamptz,
  review_lease_expires_at timestamptz,
  review_lease_version bigint     NOT NULL DEFAULT 0,
  created_at         timestamptz  NOT NULL DEFAULT now(),
  updated_at         timestamptz,
  CONSTRAINT reference_and_mode_together CHECK ((reference_sql IS NULL) = (compare_mode IS NULL)),
  CONSTRAINT approved_requires_reference CHECK (status <> 'approved' OR reference_sql IS NOT NULL)
);
CREATE INDEX question_drafts_queue_idx ON draft.question_drafts (status, review_lease_expires_at, created_at);
CREATE INDEX question_drafts_job_idx ON draft.question_drafts (job_id);

CREATE TABLE draft.review_logs (
  log_id         serial PRIMARY KEY,
  draft_id       int         NOT NULL REFERENCES draft.question_drafts (draft_id) ON DELETE CASCADE,
  stage          varchar(20) NOT NULL CHECK (stage IN ('blueprint', 'solve', 'code_check', 'semantic_audit', 'checklist', 'test_case', 'decision')),
  passed         boolean     NOT NULL,
  score          numeric(5,2),
  reasons        jsonb,
  review_model   varchar(100),
  rubric_version varchar(50),
  raw_output     text,
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX review_logs_draft_idx ON draft.review_logs (draft_id, created_at);

CREATE TABLE draft.self_solve_runs (
  run_id           serial PRIMARY KEY,
  draft_id         int         NOT NULL REFERENCES draft.question_drafts (draft_id) ON DELETE CASCADE,
  sample_index     smallint    NOT NULL,
  model_sql        text        NOT NULL,
  is_selected      boolean     NOT NULL DEFAULT false,
  matched_datasets int         NOT NULL,
  total_datasets   int         NOT NULL,
  mismatch_detail  jsonb,
  exec_status      varchar(30),
  row_count        int,
  result_hash      varchar(64),
  error            text,
  review_model     varchar(100),
  review_round     smallint    NOT NULL DEFAULT 1,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (draft_id, review_round, sample_index),
  CHECK (matched_datasets <= total_datasets)
);
CREATE UNIQUE INDEX self_solve_runs_one_selected_idx ON draft.self_solve_runs (draft_id, review_round) WHERE is_selected;

CREATE TABLE draft.llm_call_ledger (
  call_id             bigserial PRIMARY KEY,
  job_id              int REFERENCES draft.generation_jobs (job_id) ON DELETE SET NULL,
  draft_id            int REFERENCES draft.question_drafts (draft_id) ON DELETE SET NULL,
  stage               varchar(20) NOT NULL CHECK (stage IN ('planner', 'model_a', 'solve_b', 'checklist_b')),
  attempt_no          smallint    NOT NULL DEFAULT 1 CHECK (attempt_no >= 1),
  provider            varchar(30) NOT NULL CHECK (provider IN ('ollama', 'api')),
  model               varchar(100) NOT NULL,
  prompt_name         varchar(50),
  prompt_version      varchar(50),
  prompt_hash         varchar(64),
  request_hash        varchar(64),
  status              varchar(20) NOT NULL CHECK (status IN ('reserved', 'running', 'succeeded', 'failed', 'timed_out', 'cancelled')),
  started_at          timestamptz,
  finished_at         timestamptz,
  latency_ms          int CHECK (latency_ms IS NULL OR latency_ms >= 0),
  input_tokens        int CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens       int CHECK (output_tokens IS NULL OR output_tokens >= 0),
  estimated_cost_usd  numeric(12,6) CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0),
  external_request_id varchar(255),
  error_code          varchar(50),
  created_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT llm_call_finish_after_start CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX llm_call_ledger_created_idx ON draft.llm_call_ledger (created_at, status);
CREATE INDEX llm_call_ledger_job_idx ON draft.llm_call_ledger (job_id, created_at);
CREATE INDEX llm_call_ledger_draft_idx ON draft.llm_call_ledger (draft_id, created_at);

-- ============================ live: câu hỏi ===========================
CREATE TABLE live.questions (
  question_id     serial PRIMARY KEY,
  world_id        int          NOT NULL REFERENCES core.worlds (world_id),
  source_draft_id int          UNIQUE REFERENCES draft.question_drafts (draft_id),
  title           varchar(200) NOT NULL,
  question        text         NOT NULL,
  reference_sql   text         NOT NULL,
  compare_mode    varchar(20)  NOT NULL CHECK (compare_mode IN ('ordered', 'unordered')),
  difficulty      smallint     NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
  skill_ids       int[]        NOT NULL,
  tables_used     text[]       NOT NULL DEFAULT '{}',
  schema_text     text         NOT NULL DEFAULT '',
  status          varchar(20)  NOT NULL DEFAULT 'ready' CHECK (status IN ('ready', 'archived', 'retired')),
  is_source       boolean      NOT NULL DEFAULT true,
  is_flagged      boolean      NOT NULL DEFAULT false,
  pass_rate       numeric(5,2) CHECK (pass_rate BETWEEN 0 AND 100),
  created_at      timestamptz  NOT NULL DEFAULT now(),
  archived_at     timestamptz,
  retired_at      timestamptz,
  retire_reason   text,
  CONSTRAINT retired_has_timestamp CHECK (status <> 'retired' OR retired_at IS NOT NULL),
  CONSTRAINT archived_has_timestamp CHECK (status <> 'archived' OR archived_at IS NOT NULL)
);
CREATE INDEX questions_skill_ids_gin_idx ON live.questions USING gin (skill_ids);
CREATE INDEX questions_pool_idx ON live.questions (world_id, difficulty) WHERE status = 'ready';
CREATE INDEX questions_source_idx ON live.questions (world_id, difficulty) WHERE is_source AND status <> 'retired';

CREATE TABLE live.test_cases (
  test_id         serial PRIMARY KEY,
  question_id     int          NOT NULL REFERENCES live.questions (question_id) ON DELETE CASCADE,
  dataset_ref     varchar(100) NOT NULL,
  dataset_version int          NOT NULL CHECK (dataset_version >= 1),
  type            varchar(20)  NOT NULL CHECK (type IN ('standard', 'edge', 'random', 'trap')),
  expected_result jsonb        NOT NULL,
  is_hidden       boolean      NOT NULL DEFAULT false,
  UNIQUE (question_id, dataset_ref, dataset_version, type)
);

CREATE TABLE live.admin_overrides (
  id          serial PRIMARY KEY,
  admin_id    int         NOT NULL REFERENCES live.users (user_id),
  draft_id    int         REFERENCES draft.question_drafts (draft_id),
  question_id int         REFERENCES live.questions (question_id),
  action      varchar(30) NOT NULL CHECK (action IN ('approve', 'reject', 'retire', 'restore')),
  note        text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT exactly_one_target CHECK ((draft_id IS NULL) <> (question_id IS NULL))
);

CREATE TABLE live.audit_logs (
  log_id      serial PRIMARY KEY,
  actor_id    int         REFERENCES live.users (user_id),
  action      varchar(50) NOT NULL,
  entity_type varchar(50) NOT NULL,
  entity_id   varchar(50),
  detail      jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_logs_entity_idx ON live.audit_logs (entity_type, entity_id);
CREATE INDEX audit_logs_time_idx ON live.audit_logs (created_at);

INSERT INTO live.roles (name, description) VALUES ('learner', 'Người học'), ('admin', 'Quản trị viên')
ON CONFLICT (name) DO NOTHING;
