-- Bảng bài nộp (submissions), kết quả tuần (weekly_results) và thống kê người học (user_stats)
-- Tích hợp phần việc của Đạt (SQL Sandbox, Grading, Leaderboard) & Nguyên (Auth, Profile, Progress) vào chuẩn Design v7 (live.*).

CREATE TABLE IF NOT EXISTS live.submissions (
  submission_id     bigserial PRIMARY KEY,
  user_id           int          NOT NULL REFERENCES live.users (user_id) ON DELETE CASCADE,
  question_id       int          NOT NULL REFERENCES live.questions (question_id) ON DELETE CASCADE,
  set_id            int          REFERENCES live.weekly_sets (set_id) ON DELETE SET NULL,
  submitted_sql     text         NOT NULL,
  submission_status varchar(20)  NOT NULL CHECK (submission_status IN ('passed', 'failed', 'error')),
  execution_status  varchar(20)  NOT NULL CHECK (execution_status IN ('passed', 'error')),
  score             numeric(5,2) NOT NULL DEFAULT 0,
  result_json       jsonb,
  error_message     text,
  runtime_ms        int,
  submitted_at      timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS submissions_user_question_idx ON live.submissions (user_id, question_id, submitted_at DESC);
CREATE INDEX IF NOT EXISTS submissions_set_passed_idx ON live.submissions (set_id, user_id, question_id, submitted_at) WHERE submission_status = 'passed';
CREATE INDEX IF NOT EXISTS submissions_time_passed_idx ON live.submissions (submitted_at, user_id, question_id) WHERE submission_status = 'passed';
