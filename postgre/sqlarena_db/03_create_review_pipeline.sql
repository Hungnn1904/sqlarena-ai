-- =====================================================
-- 03_create_review_pipeline.sql   (chay trong sqlarena_db, sau 01 va 02)
-- Them cho pipeline kiem duyet (ai/review.py):
--   * cho phep review_logs.stage = test_case / decision
--   * mo rong draft.self_solve_runs (moi dong = 1 loi giai cua Model B)
--   * tao draft.test_cases (reference_sql + expected result theo dataset)
-- Chay lai nhieu lan van an toan. Khong dong den draft.question_drafts, core.*.
-- =====================================================

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'sqlarena_db' THEN
        RAISE EXCEPTION 'Wrong database. Connect to sqlarena_db.';
    END IF;
END $$;

ALTER TABLE draft.review_logs DROP CONSTRAINT IF EXISTS chk_review_stage;
ALTER TABLE draft.review_logs
    ADD CONSTRAINT chk_review_stage
    CHECK (stage IN ('code_check', 'self_solve', 'checklist', 'test_case', 'decision'));

ALTER TABLE draft.self_solve_runs
    ADD COLUMN IF NOT EXISTS sample_index SMALLINT,
    ADD COLUMN IF NOT EXISTS is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS exec_status VARCHAR(30),
    ADD COLUMN IF NOT EXISTS row_count INTEGER,
    ADD COLUMN IF NOT EXISTS result_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS error TEXT,
    ADD COLUMN IF NOT EXISTS review_model VARCHAR(100),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE UNIQUE INDEX IF NOT EXISTS ux_self_solve_draft_sample
    ON draft.self_solve_runs (draft_id, sample_index)
    WHERE sample_index IS NOT NULL;

CREATE TABLE IF NOT EXISTS draft.test_cases (
    test_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    draft_id BIGINT NOT NULL,
    dataset_ref VARCHAR(100) NOT NULL,
    dataset_version VARCHAR(64) NOT NULL,
    compare_mode VARCHAR(20) NOT NULL,
    reference_sql TEXT NOT NULL,
    expected_columns JSONB NOT NULL,
    expected_rows JSONB NOT NULL,
    row_count INTEGER NOT NULL,
    result_hash VARCHAR(64) NOT NULL,
    review_version VARCHAR(60) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_test_case_draft
        FOREIGN KEY (draft_id) REFERENCES draft.question_drafts(draft_id) ON DELETE CASCADE,
    CONSTRAINT chk_test_case_mode CHECK (compare_mode IN ('ordered', 'unordered')),
    CONSTRAINT chk_test_case_rows CHECK (row_count >= 0),
    CONSTRAINT uq_test_case UNIQUE (draft_id, dataset_ref, dataset_version)
);

CREATE INDEX IF NOT EXISTS idx_test_case_draft ON draft.test_cases (draft_id);

COMMIT;
