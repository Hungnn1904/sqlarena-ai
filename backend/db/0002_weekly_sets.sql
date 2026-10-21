-- Bộ đề tuần (theo Design v7). weekly_results/user_stats thuộc module chấm điểm & xếp hạng nên KHÔNG tạo ở đây.
CREATE TABLE live.weekly_sets (
  set_id       serial PRIMARY KEY,
  title        varchar(100) NOT NULL,
  week_start   date         NOT NULL UNIQUE,
  status       varchar(20)  NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'closed')),
  created_at   timestamptz  NOT NULL DEFAULT now(),
  published_at timestamptz,
  closed_at    timestamptz,
  CONSTRAINT published_has_timestamp CHECK (status = 'draft' OR published_at IS NOT NULL),
  CONSTRAINT closed_has_timestamp CHECK (status <> 'closed' OR closed_at IS NOT NULL)
);
COMMENT ON COLUMN live.weekly_sets.week_start IS 'Ngày bắt đầu tuần theo múi giờ ứng dụng (mặc định Asia/Ho_Chi_Minh).';
CREATE UNIQUE INDEX weekly_sets_one_published_idx ON live.weekly_sets (status) WHERE status = 'published';

CREATE TABLE live.weekly_set_items (
  set_id      int      NOT NULL REFERENCES live.weekly_sets (set_id) ON DELETE CASCADE,
  question_id int      NOT NULL REFERENCES live.questions (question_id),
  position    smallint NOT NULL,
  is_voided   boolean  NOT NULL DEFAULT false,
  PRIMARY KEY (set_id, question_id),
  UNIQUE (question_id),
  UNIQUE (set_id, position)
);
COMMENT ON COLUMN live.weekly_set_items.is_voided IS 'Đề bị loại khỏi bảng điểm (đề lỗi giữa tuần).';
