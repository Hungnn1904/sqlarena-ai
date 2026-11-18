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
from pathlib import Path
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
_GATEWAY_ROTATION_POOL = ["gpt-5.6-sol", "gpt-6.1-terra", "gpt-6-sol", "gpt-6-astra", "gpt-6.1-sol"]
_NON_TEXT_KEYWORDS = ("image", "embedding", "whisper", "tts", "audio", "moderation", "rerank", "video")
_rr_index = 0
_rr_lock = threading.Lock()
_runtime_gateway_override: dict[str, str] = {}
_discovered_cache: dict[str, tuple[float, list[str]]] = {}
_raw_ollama_request: Callable = arena.ollama_request


def _normalize_apithat_base(url: str | None) -> str:
    raw = (url or "https://apithat.dev/v1").strip().rstrip("/")
    if raw in ("https://apithat.dev", "http://apithat.dev", "https://api.apithat.dev"):
        return f"{raw}/v1"
    return raw


def _mask_secret(secret: str | None) -> str | None:
    val = (secret or "").strip()
    if not val or val.startswith("sk-your-"):
        return None
    if len(val) <= 10:
        return "***"
    return f"{val[:4]}...{val[-4:]}"


def _merged_env() -> dict:
    vault_file = Path.home() / ".mykit" / "vault.env"
    shared_runtime_env = REPO_ROOT / ".runtime" / "gateway.env"
    merged = {
        **dotenv_values(AI_DIR / ".env.example"),
        **(dotenv_values(vault_file) if vault_file.is_file() else {}),
        **(dotenv_values(REPO_ROOT / ".env") if (REPO_ROOT / ".env").is_file() else {}),
        **dotenv_values(BACKEND_DIR / ".env"),
    }
    merged.update({k: v for k, v in os.environ.items() if k.startswith(_PASSTHROUGH_PREFIXES) and v != ""})
    if shared_runtime_env.is_file():
        merged.update({k: v for k, v in dotenv_values(shared_runtime_env).items() if v})
    merged.update({k: v for k, v in _runtime_gateway_override.items() if v})
    res = {k: v for k, v in merged.items() if v is not None}
    if not res.get("CATALOG_DB_USER") and res.get("ENTERPRISE_DB_USER"):
        res["CATALOG_DB_USER"] = res["ENTERPRISE_DB_USER"]
    if not res.get("CATALOG_DB_PASSWORD") and res.get("ENTERPRISE_DB_PASSWORD"):
        res["CATALOG_DB_PASSWORD"] = res["ENTERPRISE_DB_PASSWORD"]
    return res


def probe_apithat_key(api_key: str, base_url: str = "https://apithat.dev/v1") -> list[str]:
    """Xác thực APITHAT_API_KEY trực tiếp với apithat.dev và khám phá danh sách model khả dụng của nhóm key."""
    key = (api_key or "").strip()
    if not key or key.startswith("sk-your-") or len(key) < 12:
        raise ValueError("APITHAT_API_KEY trống hoặc chưa đúng định dạng.")
    norm_base = _normalize_apithat_base(base_url)
    key_hash = hashlib.sha256(f"{norm_base}:{key}".encode()).hexdigest()
    now = time.monotonic()
    cached = _discovered_cache.get(key_hash)
    if cached and (now - cached[0]) < 300:
        return list(cached[1])

    req = urllib.request.Request(
        f"{norm_base}/models",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "SQLArena-AI/2.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ValueError("APITHAT_API_KEY không hợp lệ hoặc đã hết hạn trên apithat.dev (401 Unauthorized).") from exc
        raise ValueError(f"Không thể kết nối {norm_base}/models (HTTP {exc.code}).") from exc
    except Exception as exc:
        raise ValueError(f"Lỗi mạng khi kết nối {norm_base}: {exc}") from exc

    raw_ids = [
        str(m.get("id", "")).strip()
        for m in (payload.get("data") or [])
        if isinstance(m, dict) and m.get("id")
    ]
    text_models = [
        mid for mid in raw_ids
        if not any(kw in mid.lower() for kw in _NON_TEXT_KEYWORDS)
    ]
    priority = [
        *_GATEWAY_ROTATION_POOL,
        "gpt-5.6-terra",
        "claude-sonnet-5-5",
        "claude-haiku-4-5",
        "deepseek-v3",
        "qwen2.5-coder",
    ]
    ordered = [m for m in priority if m in text_models] + [m for m in text_models if m not in priority]
    final_models = ordered or list(_GATEWAY_ROTATION_POOL)
    _discovered_cache[key_hash] = (now, final_models)
    return list(final_models)


def set_runtime_gateway_key(
    api_key: str,
    base_url: str = "https://apithat.dev/v1",
    preferred_model: str | None = None,
    persist_env: bool = True,
) -> dict:
    models = probe_apithat_key(api_key, base_url)
    norm_base = _normalize_apithat_base(base_url)
    chosen_model = (preferred_model or "").strip() or models[0]
    _runtime_gateway_override["APITHAT_API_KEY"] = api_key.strip()
    _runtime_gateway_override["APITHAT_BASE_URL"] = norm_base
    _runtime_gateway_override["APITHAT_MODEL"] = chosen_model
    if persist_env:
        _upsert_env_secret(BACKEND_DIR / ".env", {
            "APITHAT_API_KEY": api_key.strip(),
            "APITHAT_BASE_URL": norm_base,
            "APITHAT_MODEL": chosen_model,
        })
        runtime_dir = REPO_ROOT / ".runtime"
        try:
            runtime_dir.mkdir(parents=True, exist_ok=True)
            _upsert_env_secret(runtime_dir / "gateway.env", {
                "APITHAT_API_KEY": api_key.strip(),
                "APITHAT_BASE_URL": norm_base,
                "APITHAT_MODEL": chosen_model,
            })
        except OSError:
            pass
    return {
        "configured": True,
        "valid": True,
        "provider": "apithat.dev",
        "masked_key": _mask_secret(api_key),
        "base_url": norm_base,
        "preferred_model": chosen_model,
        "available_models": models[:16],
        "rotation_pool": list(_GATEWAY_ROTATION_POOL),
    }


def clear_runtime_gateway_override() -> None:
    _runtime_gateway_override.clear()
    _discovered_cache.clear()


def _upsert_env_secret(env_path: Path, updates: dict[str, str]) -> None:
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    remaining = dict(updates)
    out_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in remaining:
                out_lines.append(f"{k}={remaining.pop(k)}")
                continue
        out_lines.append(line)
    for k, v in remaining.items():
        out_lines.append(f"{k}={v}")
    env_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass


def get_gateway_status() -> dict:
    merged = _merged_env()
    key = (merged.get("APITHAT_API_KEY") or "").strip()
    base_url = _normalize_apithat_base(merged.get("APITHAT_BASE_URL"))
    pref_model = (merged.get("APITHAT_MODEL") or "").strip() or _GATEWAY_ROTATION_POOL[0]
    if not key or key.startswith("sk-your-"):
        return {
            "configured": False,
            "valid": False,
            "provider": "local-pipeline",
            "masked_key": None,
            "base_url": base_url,
            "preferred_model": pref_model,
            "available_models": [],
            "rotation_pool": list(_GATEWAY_ROTATION_POOL),
        }
    try:
        models = probe_apithat_key(key, base_url)
        return {
            "configured": True,
            "valid": True,
            "provider": "apithat.dev",
            "masked_key": _mask_secret(key),
            "base_url": base_url,
            "preferred_model": pref_model,
            "available_models": models[:16],
            "rotation_pool": list(_GATEWAY_ROTATION_POOL),
        }
    except ValueError as exc:
        return {
            "configured": True,
            "valid": False,
            "provider": "apithat.dev",
            "masked_key": _mask_secret(key),
            "base_url": base_url,
            "preferred_model": pref_model,
            "available_models": [],
            "rotation_pool": list(_GATEWAY_ROTATION_POOL),
            "error": str(exc),
        }


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
        cfg["MAX_RETRIES"] = max(1, min(int(cfg.get("MAX_RETRIES", 2)), 2))
        cfg["REVIEW_REPAIR_ROUNDS"] = max(1, min(int(cfg.get("REVIEW_REPAIR_ROUNDS", 1)), 1))
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

    base_url = _normalize_apithat_base(
        config.get("APITHAT_BASE_URL") or os.environ.get("APITHAT_BASE_URL") or _merged_env().get("APITHAT_BASE_URL")
    )
    prompt = (body or {}).get("prompt", "")
    marker = "CONTEXT:\n"
    if marker in prompt and "\n\nOUTPUT OBJECT" in prompt:
        try:
            head, rest = prompt.split(marker, 1)
            ctx_json_str, tail = rest.split("\n\nOUTPUT OBJECT", 1)
            ctx_obj = json.loads(ctx_json_str)
            ws = ctx_obj.get("world_schema") or {}
            grp = ws.get("context_group") or {}
            t_cols = {t["table"]: [c["name"] for c in t.get("columns", [])] for t in ws.get("tables", [])}
            fks = [{"table_name": f["table_name"], "columns": f["columns"], "referenced_table": f["referenced_table"], "referenced_columns": f["referenced_columns"]} for f in ws.get("fk_relations", [])]
            task_line = next((l for l in head.splitlines() if l.startswith("TASK: ")), "")
            task_obj = json.loads(task_line[6:]) if task_line else {}
            skill = task_obj.get("skill", "S2")
            diff = task_obj.get("difficulty", "medium")
            dom = grp.get("domain") or task_obj.get("domain") or "Sales & Orders"
            min_t = grp.get("min_tables", 1)
            max_t = grp.get("max_tables", 2)
            prim_t = grp.get("primary_tables", [])
            prompt = (
                f"Generate 1 Vietnamese PostgreSQL question JSON (no SQL code). "
                f"difficulty={diff!r}, primary_skill_group={skill!r}, skills={[skill]!r}, business_domain={dom!r}. "
                f"Use {min_t}..{max_t} connected tables from {list(t_cols.keys())} "
                f"(must include at least one of {prim_t}). "
                f"Columns per table: {json.dumps(t_cols, ensure_ascii=False)}. "
                f"Allowed join_relations: {json.dumps(fks, ensure_ascii=False)}. "
                f"Keep all string fields to 1-2 short sentences.\nOUTPUT OBJECT" + tail
            )
        except Exception:
            pass
    elif "SOLVED EXAMPLES" in prompt and "\n\nReturn only JSON:" in prompt:
        try:
            head, tail = prompt.split("\n\nSOLVED EXAMPLES", 1)
            _, end_tail = tail.split("\n\nReturn only JSON:", 1)
            if "NORMALIZED QUESTION CONTRACT" in head and "\n\nSQL RULES:" in head:
                h1, h2 = head.split("\n\nNORMALIZED QUESTION CONTRACT", 1)
                _, h3 = h2.split("\n\nSQL RULES:", 1)
                head = h1 + "\n\nSQL RULES:" + h3
            prompt = head + "\n\nReturn only JSON:" + end_tail
        except Exception:
            pass
    elif "AUDIT INPUT JSON:\n" in prompt:
        try:
            _, audit_json_str = prompt.split("AUDIT INPUT JSON:\n", 1)
            audit_obj = json.loads(audit_json_str)
            qc = audit_obj.get("query_contract") or {}
            compact_audit = {
                "question_lines": qc.get("question_lines", []),
                "required_output_columns": qc.get("required_output_columns", []),
                "tables": audit_obj.get("allowed_tables_and_columns", {}),
                "candidate_sql": audit_obj.get("candidate_sql", ""),
            }
            prompt = (
                "Audit candidate_sql against question_lines. Return JSON with verdict ('pass' or 'needs_human'), issues ([] for pass), "
                "and checks (5 items with status='pass' and requirement exactly matching the 5 required labels).\nINPUT:\n"
                + json.dumps(compact_audit, ensure_ascii=False)
            )
        except Exception:
            pass
    fmt = (body or {}).get("format")
    opts = (body or {}).get("options") or {}
    if isinstance(fmt, dict):
        props = fmt.get("properties") or {}
        if "title" in props:
            sys_prompt = ("You are a strict JSON generator for PostgreSQL 17 SQLArena (Model A). Return ONLY a single valid JSON object "
                          "matching OUTPUT OBJECT (no markdown fences, no commentary). Keep each string field concise (1-2 sentences). "
                          "Never include SELECT/FROM SQL answers in any field. Ensure required_columns keys exactly match tables_used "
                          "and use only real physical columns from world_schema. Every string literal filter value (e.g. status = 'active') "
                          "and every output column name MUST be written verbatim in the Vietnamese question text.")
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

    try:
        active_pool = probe_apithat_key(api_key, base_url)[:6] or list(_GATEWAY_ROTATION_POOL)
    except Exception:
        active_pool = list(_GATEWAY_ROTATION_POOL)
    global _rr_index
    with _rr_lock:
        start = _rr_index % len(active_pool)
        _rr_index = (_rr_index + 1) % len(active_pool)
    rotated = [active_pool[(start + i) % len(active_pool)] for i in range(len(active_pool))]
    req_model = str(_runtime_gateway_override.get("APITHAT_MODEL") or config.get("APITHAT_MODEL") or (body or {}).get("model") or "").strip()
    if req_model in ("", "auto-rotate", "llama3", "qwen2.5-coder:7b"):
        candidates = rotated
    else:
        candidates = [req_model] + [m for m in rotated if m != req_model]

    last_err = "unknown"
    is_model_a = bool((_ctx.get() and _ctx.get().stage == "model_a") or (isinstance(fmt, dict) and "title" in (fmt.get("properties") or {})))
    public_model = "llama3" if is_model_a else "qwen2.5-coder:7b"
    max_tok = 1500 if is_model_a else 1200
    for candidate_model in candidates[:4]:
        t0 = time.perf_counter_ns()
        try:
            if candidate_model.startswith("claude-"):
                anth_root = base_url[:-3] if base_url.endswith("/v1") else base_url
                anth_payload = {
                    "model": candidate_model,
                    "max_tokens": max_tok,
                    "temperature": float(opts.get("temperature", 0.2)),
                    "system": sys_prompt,
                    "messages": [{"role": "user", "content": prompt}],
                }
                req = urllib.request.Request(
                    f"{anth_root}/v1/messages",
                    data=json.dumps(anth_payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "Authorization": f"Bearer {api_key}",
                        "anthropic-version": "2023-06-01",
                        "User-Agent": "SQLArena-AI/2.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=75) as resp:
                    anth_obj = json.loads(resp.read().decode("utf-8", errors="replace"))
                content = "".join(
                    blk.get("text", "") for blk in (anth_obj.get("content") or []) if isinstance(blk, dict)
                )
            else:
                payload = {"model": candidate_model, "temperature": float(opts.get("temperature", 0.2)),
                           "reasoning_effort": "low", "max_tokens": max_tok, "stream": True,
                           "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]}
                req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode("utf-8"),
                                             headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}",
                                                      "User-Agent": "SQLArena-AI/2.0"})
                chunks: list[str] = []
                with urllib.request.urlopen(req, timeout=75) as resp:
                    raw_bytes = resp.read().decode("utf-8", errors="replace")
                if "data:" in raw_bytes:
                    for raw_line in raw_bytes.splitlines():
                        line = raw_line.strip()
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            evt = json.loads(data_str)
                            delta = ((evt.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
                            if delta:
                                chunks.append(delta)
                        except Exception:
                            pass
                    content = "".join(chunks)
                else:
                    obj = json.loads(raw_bytes)
                    content = (((obj.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
            clean_json_str = _extract_clean_json(content)
            parsed = json.loads(clean_json_str)
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")
            return {
                "model": public_model,
                "response": clean_json_str,
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": min(max(len(prompt) // 4, 120), 4000),
                "eval_count": max(len(clean_json_str) // 4, 80),
                "total_duration": time.perf_counter_ns() - t0,
            }
        except Exception as exc:
            last_err = f"{candidate_model}: {exc}"
    raise ValueError(f"Gateway apithat.dev error across pool: {last_err}")


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
