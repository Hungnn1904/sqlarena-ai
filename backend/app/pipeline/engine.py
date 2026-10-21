"""Cầu nối tới engine AI hiện có trong thư mục `ai/` (Model A: main.py, Model B: review.py, validator.py...).

Nguyên tắc: KHÔNG sửa logic của `ai/`. Backend chỉ
  1. nạp engine vào sys.path và cấp cấu hình (thay cho `ai/.env` + CLI tương tác),
  2. thay phần truy cập DB cũ (CLI ghi thẳng schema v1) bằng repository của backend,
  3. chèn một lớp chặn duy nhất quanh lệnh gọi Ollama để áp BudgetGuard + ghi llm_call_ledger.
"""
import contextvars
import hashlib
import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable

from dotenv import dotenv_values

from ..config import BACKEND_DIR, REPO_ROOT

AI_DIR = REPO_ROOT / "ai"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

import main as arena          # noqa: E402  (ai/main.py - Model A)
import review as rv           # noqa: E402  (ai/review.py - Model B)
import validator as vd        # noqa: E402

_PASSTHROUGH_PREFIXES = ("REVIEW_", "OLLAMA_", "MODEL_", "CATALOG_DB_", "ENTERPRISE_DB_", "GENERATION_", "RETRY_",
                         "MAX_", "STATEMENT_", "DUPLICATE_", "WORLD_ID", "RULES_PATH", "AI_PROVIDER")


def _merged_env() -> dict:
    merged = {**dotenv_values(AI_DIR / ".env.example"), **dotenv_values(BACKEND_DIR / ".env")}
    merged.update({k: v for k, v in os.environ.items() if k.startswith(_PASSTHROUGH_PREFIXES)})
    return {k: v for k, v in merged.items() if v is not None}


def load_engine_config(overrides: dict | None = None) -> dict:
    """Cấu hình engine = ai/.env.example < backend/.env < biến môi trường < overrides.
    Dùng lại đúng bước kiểm tra/ép kiểu của engine (arena.load_config + rv.load_review_config)."""
    merged = _merged_env()
    arena.dotenv_values = lambda *_a, **_k: dict(merged)     # engine đọc cấu hình qua hàm này
    return rv.load_review_config(env=overrides)


# ----------------------------------------------------------------------------- LLM ledger interceptor

class BudgetExceeded(Exception):
    """Cố ý KHÔNG kế thừa ValueError để không bị các `except ValueError` của engine nuốt mất."""


@dataclass
class LlmContext:
    job_id: int | None
    draft_id: int | None
    stage: str                    # model_a | solve_b | checklist_b
    prompt_name: str
    prompt_version: str
    attempt_no: int = 1


_ctx: contextvars.ContextVar[LlmContext | None] = contextvars.ContextVar("llm_ctx", default=None)
_original_request: Callable = arena.ollama_request
_transport: Callable = _original_request
_semaphore = threading.BoundedSemaphore(1)
_reserve: Callable[[LlmContext, dict], int] | None = None
_finish: Callable[..., None] | None = None


@contextmanager
def llm_context(**kwargs):
    token = _ctx.set(LlmContext(**kwargs))
    try:
        yield
    finally:
        _ctx.reset(token)


def set_transport(fn: Callable | None) -> None:
    """Thay transport HTTP tới Ollama (test dùng FakeOllama). None = Ollama thật."""
    global _transport
    _transport = fn or _original_request


def set_concurrency(n: int) -> None:
    global _semaphore
    _semaphore = threading.BoundedSemaphore(max(1, n))


def _is_timeout(exc: Exception) -> bool:
    return "timeout" in str(exc).lower() or "không phản hồi" in str(exc).lower() or "khong phan hoi" in str(exc).lower()


def ledgered_request(config: dict, path: str, body: dict | None = None):
    if path != "/api/generate":                       # /api/tags... không tốn call sinh
        return _transport(config, path, body)
    ctx = _ctx.get()
    if ctx is None or _reserve is None or _finish is None:
        raise RuntimeError("Gọi LLM ngoài llm_context/ledger: bị chặn (fail closed).")
    prompt = (body or {}).get("prompt", "")
    meta = {"model": (body or {}).get("model", "?"),
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
            "request_hash": hashlib.sha256(json.dumps({k: v for k, v in (body or {}).items()}, sort_keys=True, default=str).encode()).hexdigest()}
    call_id = _reserve(ctx, meta)                     # raise BudgetExceeded nếu hết ngân sách (atomic, có khóa)
    with _semaphore:
        started = time.perf_counter()
        _finish(call_id, "running", None)
        try:
            result = _transport(config, path, body)
        except Exception as exc:
            _finish(call_id, "timed_out" if _is_timeout(exc) else "failed", {"latency_ms": int((time.perf_counter() - started) * 1000),
                                                                                "error_code": type(exc).__name__})
            raise
        _finish(call_id, "succeeded", {"latency_ms": int((time.perf_counter() - started) * 1000),
                                       "input_tokens": result.get("prompt_eval_count") if isinstance(result, dict) else None,
                                       "output_tokens": result.get("eval_count") if isinstance(result, dict) else None})
        return result


def install_ledger(reserve: Callable[[LlmContext, dict], int], finish: Callable[..., None]) -> None:
    global _reserve, _finish
    _reserve, _finish = reserve, finish
    arena.ollama_request = ledgered_request           # main.generate và review.call_* đều tra cứu thuộc tính này lúc gọi
