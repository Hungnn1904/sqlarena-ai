-- Cho phép ghi nhận hành động chuyển ngược draft từ approved về needs_human trong live.admin_overrides.
ALTER TABLE live.admin_overrides DROP CONSTRAINT IF EXISTS admin_overrides_action_check;
ALTER TABLE live.admin_overrides
  ADD CONSTRAINT admin_overrides_action_check
  CHECK (action IN ('approve', 'reject', 'retire', 'restore', 'return_needs_human'));
