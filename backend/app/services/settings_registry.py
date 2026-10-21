"""SettingsRegistry: mọi key trong core.system_settings phải được đăng ký (kiểu, min/max, quyền sửa, hard cap)."""
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection

from ..db import ex, q, q1
from ..errors import bad_request, not_found


@dataclass(frozen=True)
class Spec:
    type: type
    default: Any
    description: str
    minimum: float | None = None
    maximum: float | None = None
    hard_max: float | None = None          # trần an toàn: API không được nới
    mutable: bool = True
    restart_required: bool = False


REGISTRY: dict[str, Spec] = {
    "generation.daily_budget_calls": Spec(int, 300, "Trần số lần gọi LLM mỗi ngày (tính cả call lỗi/timeout đã gửi)", 1, 100000, 100000),
    "generation.lease_seconds": Spec(int, 120, "Thời hạn lease của job/draft; heartbeat gia hạn định kỳ", 15, 3600, 3600),
    "generation.heartbeat_seconds": Spec(int, 20, "Chu kỳ heartbeat", 3, 300, 300),
    "generation.max_attempts": Spec(int, 3, "Số lần claim tối đa của một job/draft trước khi failed(system)", 1, 10, 10),
    "generation.max_quantity": Spec(int, 30, "Số draft tối đa một job", 1, 30, 30),
    "solve.samples_k": Spec(int, 3, "Số lời giải Model B cho mỗi đề", 1, 7, 7),
    "solve.consensus": Spec(str, "all", "Chỉ hỗ trợ all", mutable=False),
    "llm.max_concurrent": Spec(int, 1, "Số call LLM đồng thời tối đa tại worker", 1, 8, 8, restart_required=True),
    "weekly.question_count": Spec(dict, {"1": 5, "2": 10, "3": 5}, "Mục tiêu mỗi tuần theo độ khó {1:Easy,2:Medium,3:Hard} (tài liệu chốt: 20 câu = 5/10/5)", hard_max=100),
    "weekly.close_requires_cutoff": Spec(bool, False, "Bật để chỉ cho đóng tuần sau mốc kết thúc (week_start + 7 ngày). Mặc định tắt: admin chủ động đóng tuần cũ để chuyển bộ mới"),
    "review.checklist_enabled": Spec(bool, False, "Chạy checklist LLM bổ sung (mặc định tắt)", mutable=False),
}


def ensure_defaults(conn: Connection) -> None:
    import json
    for key, spec in REGISTRY.items():
        ex(conn, "INSERT INTO core.system_settings(key, value, description) VALUES (:k, CAST(:v AS jsonb), :d) ON CONFLICT (key) DO NOTHING",
           k=key, v=json.dumps(spec.default), d=spec.description)


def get(conn: Connection, key: str) -> Any:
    spec = REGISTRY[key]
    row = q1(conn, "SELECT value FROM core.system_settings WHERE key=:k", k=key)
    return row["value"] if row else spec.default


def list_all(conn: Connection) -> list[dict]:
    rows = {r["key"]: r for r in q(conn, "SELECT key, value, description, updated_at FROM core.system_settings")}
    out = []
    for key, spec in REGISTRY.items():
        r = rows.get(key)
        out.append({"key": key, "value": r["value"] if r else spec.default, "description": spec.description,
                    "updated_at": r["updated_at"] if r else None, "mutable": spec.mutable,
                    "restart_required": spec.restart_required})
    return out


def validate(key: str, value: Any) -> Any:
    spec = REGISTRY.get(key)
    if spec is None:
        raise not_found(f"Cấu hình '{key}' chưa được đăng ký")
    if not spec.mutable:
        raise bad_request(f"Cấu hình '{key}' không được sửa qua API", {"key": key})
    ok = isinstance(value, spec.type) and not (spec.type is int and isinstance(value, bool))
    if not ok:
        raise bad_request(f"Giá trị của '{key}' phải kiểu {spec.type.__name__}", {"key": key})
    if spec.type is dict:
        ok_keys = isinstance(value, dict) and set(value) <= {"1", "2", "3"} and all(
            isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in value.values())
        if not ok_keys or not 0 < sum(value.values()) <= spec.hard_max:
            raise bad_request(f"'{key}' phải là {{\"1\":n,\"2\":n,\"3\":n}} (số nguyên ≥ 0), tổng trong (0, {int(spec.hard_max)}]", {"key": key})
        return {k: int(value.get(k, 0)) for k in ("1", "2", "3")}
    if spec.type in (int, float):
        if spec.minimum is not None and value < spec.minimum or spec.maximum is not None and value > spec.maximum:
            raise bad_request(f"'{key}' phải trong [{spec.minimum}, {spec.maximum}]", {"key": key})
        if spec.hard_max is not None and value > spec.hard_max:
            raise bad_request(f"'{key}' vượt trần an toàn {spec.hard_max}", {"key": key})
    return value
