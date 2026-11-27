-- Bình chọn câu hỏi (👍/👎) và Báo lỗi / Góp ý (🚩 Human-in-the-loop) từ người học.
CREATE TABLE IF NOT EXISTS live.question_votes (
  question_id int         NOT NULL REFERENCES live.questions (question_id) ON DELETE CASCADE,
  user_id     int         NOT NULL REFERENCES live.users (user_id) ON DELETE CASCADE,
  vote        smallint    NOT NULL CHECK (vote IN (1, -1)),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (question_id, user_id)
);

CREATE TABLE IF NOT EXISTS live.question_reports (
  report_id   serial      PRIMARY KEY,
  question_id int         NOT NULL REFERENCES live.questions (question_id) ON DELETE CASCADE,
  user_id     int         NOT NULL REFERENCES live.users (user_id) ON DELETE CASCADE,
  reason_type varchar(40) NOT NULL CHECK (reason_type IN (
    'ambiguous_prompt',
    'wrong_difficulty',
    'wrong_answer_or_testcase',
    'typo_or_column_name',
    'other'
  )),
  comment     text        NOT NULL,
  status      varchar(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'dismissed')),
  admin_note  text,
  resolved_by int         REFERENCES live.users (user_id) ON DELETE SET NULL,
  resolved_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_question_reports_one_open_per_user
  ON live.question_reports (question_id, user_id)
  WHERE status = 'open';

CREATE INDEX IF NOT EXISTS idx_question_reports_question_status
  ON live.question_reports (question_id, status);
