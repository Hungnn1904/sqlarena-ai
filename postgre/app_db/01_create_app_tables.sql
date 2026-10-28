-- SQLArena application tables.
-- Run this file while connected to sqlarena_db.
-- This file intentionally keeps the application schema simple:
-- tables, primary keys, foreign keys, and one learner seed row only.

DO $$
BEGIN
    IF current_database() <> 'sqlarena_db' THEN
        RAISE EXCEPTION 'Wrong database. Connect to sqlarena_db.';
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    role VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.submissions (
    submission_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app.users(user_id),
    question_id VARCHAR(30) NOT NULL REFERENCES core.source_questions(question_id),
    submitted_sql TEXT NOT NULL,
    submission_status VARCHAR(30) NOT NULL,
    score NUMERIC(5,2),
    execution_status VARCHAR(30) NOT NULL,
    result_json JSONB,
    error_message TEXT,
    runtime_ms INTEGER,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.weekly_sets (
    set_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    set_name VARCHAR(150) NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.weekly_set_questions (
    set_id BIGINT NOT NULL REFERENCES app.weekly_sets(set_id),
    question_id VARCHAR(30) NOT NULL REFERENCES core.source_questions(question_id),
    position INTEGER NOT NULL,
    PRIMARY KEY (set_id, question_id)
);

INSERT INTO app.users
    (username, email, password_hash, display_name, role, status)
VALUES
    ('learner_demo', 'learner_demo@sqlarena.local', 'demo-only-password-hash', 'Learner Demo', 'learner', 'active'),
    ('learner_test_2', 'learner_test_2@sqlarena.local', 'demo-only-password-hash', 'Learner Test 2', 'learner', 'active'),
    ('learner_test_3', 'learner_test_3@sqlarena.local', 'demo-only-password-hash', 'Learner Test 3', 'learner', 'active')
ON CONFLICT (username) DO NOTHING;

-- Temporary weekly set for local testing (current week).
INSERT INTO app.weekly_sets
    (set_name, starts_at, ends_at, status)
SELECT
    'SQLArena Week 2026-10-26',
    TIMESTAMPTZ '2026-10-19 00:00:00+07',
    TIMESTAMPTZ '2026-11-30 00:00:00+07',
    'published'
WHERE NOT EXISTS (
    SELECT 1 FROM app.weekly_sets
    WHERE set_name = 'SQLArena Week 2026-10-26'
);

INSERT INTO app.weekly_set_questions (set_id, question_id, position)
SELECT s.set_id, v.question_id, v.position
FROM app.weekly_sets s
JOIN (VALUES
    ('ENT-001', 1),
    ('ENT-002', 2),
    ('ENT-003', 3),
    ('ENT-004', 4),
    ('ENT-005', 5),
    ('ENT-006', 6),
    ('ENT-008', 7),
    ('ENT-009', 8),
    ('ENT-010', 9),
    ('ENT-021', 10)
) AS v(question_id, position) ON TRUE
WHERE s.set_name = 'SQLArena Week 2026-10-26'
ON CONFLICT DO NOTHING;
