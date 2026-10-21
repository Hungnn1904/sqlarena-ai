"""Hằng số/chuyển đổi miền: độ khó 1/2/3 ↔ easy/medium/hard, trạng thái hợp lệ."""
DIFF_NAME = {1: "easy", 2: "medium", 3: "hard"}
DIFF_NUM = {v: k for k, v in DIFF_NAME.items()}
DRAFT_STATUSES = ("pending", "reviewing", "approved", "rejected", "needs_human")
JOB_STATUSES = ("queued", "running", "done", "failed")
QUESTION_STATUSES = ("ready", "archived", "retired")
