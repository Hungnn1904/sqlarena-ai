-- Nhóm câu hỏi nháp (Question Groups) để Giảng viên gom đề và phát hành hàng loạt.
CREATE TABLE live.question_groups (
  group_id         serial PRIMARY KEY,
  name             varchar(120) NOT NULL,
  description      text,
  status           varchar(20)  NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  published_set_id int          REFERENCES live.weekly_sets (set_id) ON DELETE SET NULL,
  created_by       int          REFERENCES live.users (user_id) ON DELETE SET NULL,
  created_at       timestamptz  NOT NULL DEFAULT now(),
  published_at     timestamptz
);

CREATE TABLE live.question_group_items (
  group_id    int      NOT NULL REFERENCES live.question_groups (group_id) ON DELETE CASCADE,
  question_id int      NOT NULL REFERENCES live.questions (question_id) ON DELETE CASCADE,
  position    smallint NOT NULL,
  PRIMARY KEY (group_id, question_id),
  UNIQUE (group_id, position)
);
