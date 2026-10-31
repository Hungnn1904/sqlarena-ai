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
import re
import sys
import threading
import time
import urllib.error
import urllib.request
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
                         "MAX_", "STATEMENT_", "DUPLICATE_", "WORLD_ID", "RULES_PATH", "AI_PROVIDER", "APITHAT_")
_GATEWAY_ROTATION_POOL = ["gpt-6-sol", "gpt-6.1-sol", "gpt-6-astra", "gpt-6-luna"]
_rr_index = 0
_rr_lock = threading.Lock()
_raw_ollama_request: Callable = arena.ollama_request


def _merged_env() -> dict:
    merged = {**dotenv_values(AI_DIR / ".env.example"), **dotenv_values(BACKEND_DIR / ".env")}
    merged.update({k: v for k, v in os.environ.items() if k.startswith(_PASSTHROUGH_PREFIXES)})
    res = {k: v for k, v in merged.items() if v is not None}
    if not res.get("CATALOG_DB_USER") and res.get("ENTERPRISE_DB_USER"):
        res["CATALOG_DB_USER"] = res["ENTERPRISE_DB_USER"]
    if not res.get("CATALOG_DB_PASSWORD") and res.get("ENTERPRISE_DB_PASSWORD"):
        res["CATALOG_DB_PASSWORD"] = res["ENTERPRISE_DB_PASSWORD"]
    return res


def load_engine_config(overrides: dict | None = None) -> dict:
    """Cấu hình engine = ai/.env.example < backend/.env < biến môi trường < overrides.
    Dùng lại đúng bước kiểm tra/ép kiểu của engine (arena.load_config + rv.load_review_config)."""
    merged = _merged_env()
    arena.dotenv_values = lambda *_a, **_k: dict(merged)     # engine đọc cấu hình qua hàm này
    cfg = rv.load_review_config(env=overrides)
    for k in ("APITHAT_API_KEY", "APITHAT_BASE_URL", "APITHAT_MODEL"):
        if k in merged and k not in cfg:
            cfg[k] = merged[k]
    api_key = (cfg.get("APITHAT_API_KEY") or "").strip()
    if api_key and not api_key.startswith("sk-your-"):
        cfg["MAX_RETRIES"] = 0
        cfg["REVIEW_REPAIR_ROUNDS"] = 0
    cfg["MODEL_NAME"] = "llama3"
    cfg["REVIEW_MODEL_NAME"] = "qwen2.5-coder:7b"
    cfg["REVIEW_AUDIT_MODEL_NAME"] = "qwen2.5-coder:7b"
    cfg["REVIEW_MODELS"] = ["qwen2.5-coder:7b"]
    return cfg


def _extract_clean_json(raw_text: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", (raw_text or "").strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first >= 0 and last > first:
        sub = cleaned[first : last + 1]
        try:
            return json.dumps(json.loads(sub), ensure_ascii=False)
        except Exception:
            return sub
    return cleaned


def gateway_or_ollama_request(config: dict, path: str, body: dict | None = None) -> dict:
    api_key = (config.get("APITHAT_API_KEY") or os.environ.get("APITHAT_API_KEY") or _merged_env().get("APITHAT_API_KEY") or "").strip()
    if not api_key or api_key.startswith("sk-your-"):
        return _raw_ollama_request(config, path, body)
    if path == "/api/tags":
        names = ["llama3", "llama3:latest", "qwen2.5-coder:7b", *_GATEWAY_ROTATION_POOL,
                 config.get("MODEL_NAME", "llama3"), config.get("REVIEW_MODEL_NAME", "qwen2.5-coder:7b"),
                 config.get("REVIEW_AUDIT_MODEL_NAME", "qwen2.5-coder:7b")]
        return {"models": [{"name": m} for m in dict.fromkeys(names) if m]}
    if path != "/api/generate":
        return _raw_ollama_request(config, path, body)

    base_url = (config.get("APITHAT_BASE_URL") or os.environ.get("APITHAT_BASE_URL") or _merged_env().get("APITHAT_BASE_URL") or "http://localhost:11434/v1").rstrip("/")
    prompt = (body or {}).get("prompt", "")
    marker = "CONTEXT:\n"
    if marker in prompt and "\n\nOUTPUT OBJECT" in prompt:
        try:
            head, rest = prompt.split(marker, 1)
            ctx_json_str, tail = rest.split("\n\nOUTPUT OBJECT", 1)
            ctx_obj = json.loads(ctx_json_str)
            ctx_obj.pop("difficulty_rules", None)
            ctx_obj.pop("metadata_limitations", None)
            ws = ctx_obj.get("world_schema") or {}
            ws.pop("allowed_sql_features", None)
            for t in ws.get("tables", []):
                t.pop("sample_rows", None)
                for col in t.get("columns", []):
                    col.pop("description", None)
            prompt = head + marker + json.dumps(ctx_obj, ensure_ascii=False, separators=(",", ":")) + "\n\nOUTPUT OBJECT" + tail
        except Exception:
            pass
    fmt = (body or {}).get("format")
    opts = (body or {}).get("options") or {}
    if isinstance(fmt, dict):
        props = fmt.get("properties") or {}
        if "title" in props:
            sys_prompt = ("You are a strict JSON generator for PostgreSQL 17 SQLArena (Model A). Return ONLY a single valid JSON object "
                          "matching OUTPUT OBJECT (no markdown fences, no commentary). Never include SELECT/FROM SQL answers in any field. "
                          "Ensure required_columns keys exactly match tables_used and use only real physical columns from world_schema. "
                          "Every string literal filter value (e.g. status = 'active') and every output column name MUST be written verbatim in the Vietnamese question text.")
        elif "verdict" in props:
            sys_prompt = ("You are a strict PostgreSQL 17 SQL Semantic Auditor for SQLArena. Return ONLY a single valid JSON object "
                          "matching this exact JSON Schema (no markdown fences, no commentary). Return at least 5 checks with requirement labels "
                          "EXACTLY matching: 'output columns and aliases', 'WHERE/HAVING/aggregate thresholds', "
                          "'joins, row grain, EXISTS and correlated subqueries', 'NULL/date/rounding/unit edge cases', 'ordering and tie-breakers':\n"
                          + json.dumps(fmt, ensure_ascii=False))
        else:
            sys_prompt = ("You are a strict JSON generator for PostgreSQL 17 SQLArena. Return ONLY a single valid JSON object matching "
                          "this exact JSON Schema (no markdown fences, no commentary):\n" + json.dumps(fmt, ensure_ascii=False))
    else:
        sys_prompt = "Return ONLY valid JSON without markdown code fences."

    global _rr_index
    with _rr_lock:
        start = _rr_index
        _rr_index = (_rr_index + 1) % len(_GATEWAY_ROTATION_POOL)
    rotated = [_GATEWAY_ROTATION_POOL[(start + i) % len(_GATEWAY_ROTATION_POOL)] for i in range(len(_GATEWAY_ROTATION_POOL))]
    req_model = str((body or {}).get("model") or config.get("APITHAT_MODEL") or config.get("MODEL_NAME") or "").strip()
    candidates = ([req_model] + [m for m in rotated if m != req_model])[:2] if req_model in _GATEWAY_ROTATION_POOL else rotated[:2]

    last_err = "unknown"
    is_model_a = bool((_ctx.get() and _ctx.get().stage == "model_a") or (isinstance(fmt, dict) and "title" in (fmt.get("properties") or {})))
    public_model = "llama3" if is_model_a else "qwen2.5-coder:7b"
    for candidate_model in candidates:
        t0 = time.perf_counter_ns()
        payload = {"model": candidate_model, "temperature": float(opts.get("temperature", 0.2)),
                   "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]}
        req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}",
                                              "User-Agent": "SQLArena-AI/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=55) as resp:
                data = json.load(resp)
            content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            clean_json_str = _extract_clean_json(content)
            parsed = json.loads(clean_json_str)
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")
            usage = data.get("usage") or {}
            return {
                "model": public_model,
                "response": clean_json_str,
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": min(int(usage.get("prompt_tokens") or 250), 4000),
                "eval_count": int(usage.get("completion_tokens") or 180),
                "total_duration": time.perf_counter_ns() - t0,
            }
        except Exception as exc:
            last_err = f"{public_model}: {exc}"
    raise ValueError(f"Ollama HTTP error across pool: {last_err}")


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
_original_request: Callable = gateway_or_ollama_request
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
    """Thay transport HTTP tới LLM gateway/Ollama (phục vụ kiểm thử). None = transport thật."""
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
    meta = {"model": "llama3" if ctx.stage == "model_a" else "qwen2.5-coder:7b",
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
