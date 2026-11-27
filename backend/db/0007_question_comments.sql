-- Thảo luận / Bình luận học tập công khai theo từng bài SQL (tách biệt hoàn toàn với live.question_reports).
CREATE TABLE IF NOT EXISTS live.question_comments (
  comment_id        serial      PRIMARY KEY,
  question_id       int         NOT NULL REFERENCES live.questions (question_id) ON DELETE CASCADE,
  user_id           int         NOT NULL REFERENCES live.users (user_id) ON DELETE CASCADE,
  parent_comment_id int         REFERENCES live.question_comments (comment_id) ON DELETE CASCADE,
  content           text        NOT NULL CHECK (char_length(btrim(content)) BETWEEN 2 AND 2000),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_question_comments_question_created
  ON live.question_comments (question_id, created_at);

CREATE INDEX IF NOT EXISTS idx_question_comments_parent
  ON live.question_comments (parent_comment_id);
