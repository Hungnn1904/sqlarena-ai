"""Tổng hợp tiến trình thời gian thực (5 bước) & Hồ sơ nghiệm thu kỹ thuật (5 khối) cho bản nháp AI."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Connection

from ..db import q

_LEGACY_MODEL_TOKENS = ("llama", "qwen", "deepseek", "ollama")

REASON_EXPLANATIONS: dict[str, str] = {
    "consensus_disagreement": "Các mẫu giải độc lập của Model B trả về tập dữ liệu lệch nhau.",
    "order_disagreement": "Các mẫu giải khớp dữ liệu nhưng khác thứ tự dòng kết quả.",
    "empty_result": "Truy vấn thực thi trên Enterprise DB trả về 0 dòng dữ liệu.",
    "required_order_by_missing": "Đề bài có yêu cầu sắp xếp nhưng câu lệnh SQL thiếu mệnh đề ORDER BY.",
    "order_by_contract_mismatch": "Mệnh đề ORDER BY chưa khớp cột hoặc chiều tăng/giảm đề bài yêu cầu.",
    "order_tiebreaker_missing": "Mệnh đề ORDER BY thiếu khóa phụ phân định khi trùng giá trị sắp xếp.",
    "output_columns_mismatch": "Danh sách tên cột đầu ra chưa khớp với tên cột tường minh trong đề bài.",
    "unstated_string_literal": "Câu lệnh SQL chứa hằng chuỗi điều kiện không được nêu trong đề bài.",
    "hardcoded_id_literal": "Câu lệnh SQL gắn cứng mã định danh số cụ thể không có trong đề bài.",
    "suspected_duplicate": "Độ tương đồng văn bản hoặc chữ ký logic cao so với câu hỏi đã có trong kho.",
    "semantic_audit_flagged": "Bộ kiểm toán ngữ nghĩa phát hiện điểm chưa khớp với yêu cầu nghiệp vụ.",
    "insufficient_valid_solutions": "Số mẫu lời giải hợp lệ của Model B chưa đạt ngưỡng tối thiểu.",
    "no_valid_solution": "Model B chưa sinh được câu lệnh SQL chạy thành công trên cơ sở dữ liệu.",
    "tables_mismatch": "Tập bảng truy vấn thực tế khác với tập bảng khai báo của bản nháp.",
    "one_to_many_join_may_duplicate_output_grain": "Phép nối bảng 1-N có nguy cơ làm nhân bản số dòng thực thể chính.",
}

STEP_LABELS: dict[int, str] = {
    1: "Model A — Sinh đề bài & Chữ ký logic",
    2: "Validator — Kiểm tra Schema, Luật độ khó & Trùng đề",
    3: "Model B — Giải đề độc lập (Blind Solving)",
    4: "Thực thi PostgreSQL & Kiểm tra đồng thuận",
    5: "Kiểm toán ngữ nghĩa & Chốt Test Cases",
}


def clean_model_name(model_val: str | None, fallback: str = "Model B") -> str:
    raw = (model_val or "").strip()
    if not raw or any(tok in raw.lower() for tok in _LEGACY_MODEL_TOKENS):
        return fallback
    return raw


def parse_solve_prompt_tag(prompt_name: str | None) -> tuple[int | None, int | None, int]:
    if not prompt_name:
        return None, None, 0
    m = re.match(r"^solve_b:s(\d+)_k(\d+)_r(\d+)$", prompt_name.strip())
    if not m:
        return None, None, 0
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def scrub_legacy_tokens(text: str | None) -> str | None:
    if not text:
        return text
    out = str(text)
    for banned in _LEGACY_MODEL_TOKENS:
        out = re.sub(rf"(?i)[\w.:\-]*{banned}[\w.:\-]*", "AI Gateway", out)
    return out


def format_error_alert(err_raw: str | None) -> str | None:
    if not err_raw:
        return None
    txt = scrub_legacy_tokens(str(err_raw).strip()) or ""
    if not txt:
        return None
    low = txt.lower()
    if "403" in low or "quota" in low or "insufficient" in low:
        return "Lỗi HTTP 403: Hết hạn mức hoặc từ chối quyền trên Gateway"
    if "401" in low or "unauthorized" in low or "invalid_api_key" in low:
        return "Lỗi HTTP 401: Khóa API Gateway không hợp lệ hoặc đã hết hạn"
    if "429" in low or "rate" in low:
        return "Lỗi HTTP 429: Vượt giới hạn tần suất gọi Gateway (Rate Limit)"
    if "timeout" in low or "timed_out" in low or "deadline" in low:
        return "Lỗi Timeout mạng khi gọi cổng AI"
    if "budget" in low or "trần" in low:
        return "Đã chạm trần ngân sách gọi AI trong ngày"
    if "orphaned" in low or "reload_restart" in low:
        return None
    return f"Cảnh báo thực thi: {txt[:140]}"


def derive_pedagogical_traps(cand: dict | None, world_schema: dict | None = None) -> list[str]:
    cand = cand or {}
    existing = cand.get("traps")
    if isinstance(existing, list):
        cleaned = [str(x).strip() for x in existing if str(x).strip()]
        if cleaned:
            return cleaned[:5]

    traps: list[str] = []
    tables = list(cand.get("tables_used") or [])
    req_cols = cand.get("required_columns") if isinstance(cand.get("required_columns"), dict) else {}
    sig = cand.get("logic_signature") if isinstance(cand.get("logic_signature"), dict) else {}
    skills = set(cand.get("skills") or [])
    q_txt = str(cand.get("question") or "")

    nullable_cols: list[str] = []
    for tbl in (world_schema or {}).get("tables") or []:
        tname = tbl.get("table")
        wanted = set(req_cols.get(tname) or [])
        for col in tbl.get("columns") or []:
            if col.get("name") in wanted and col.get("nullable"):
                nullable_cols.append(f"{tname}.{col['name']}")
    if nullable_cols or "null" in q_txt.lower():
        sample_cols = ", ".join(nullable_cols[:3]) if nullable_cols else "các cột tùy chọn"
        traps.append(f"Xử lý đúng giá trị NULL trên {sample_cols} để không làm rơi bản ghi hoặc sai phép tính.")

    filt = str(sig.get("filter_pattern") or "").strip()
    if filt and filt.lower() != "none":
        traps.append(f"Áp dụng đúng điều kiện lọc nghiệp vụ ({filt[:90]}) trước khi tổng hợp kết quả.")

    if len(tables) >= 2 or "S2" in skills:
        traps.append(f"Kết nối đúng khóa ngoại giữa {', '.join(tables[:3])} để tránh nhân bản dòng dữ liệu (quan hệ 1-N).")

    agg = str(sig.get("aggregation_pattern") or "").strip()
    if (agg and agg.lower() != "none") or "S3" in skills:
        traps.append("Phân biệt điều kiện lọc từng dòng (WHERE) với điều kiện lọc nhóm sau gom cụm (HAVING).")

    if re.search(r"(?i)\b(?:sắp xếp|tăng dần|giảm dần|order\s+by)\b", q_txt):
        traps.append(" Tuân thủ đúng chiều sắp xếp ORDER BY và khóa phụ khi các dòng có cùng giá trị.".strip())

    if not traps and tables:
        traps.append(f"Đối chiếu đúng tên cột đầu ra và kiểu dữ liệu thực tế trên bảng {', '.join(tables[:2])}.")
    return traps[:4]


def attach_live_progress(conn: Connection, items: list[dict], samples_k_default: int = 3) -> list[dict]:
    if not items:
        return items
    draft_ids = [int(it["draft_id"]) for it in items if it.get("draft_id") is not None]
    job_ids = list({int(it["job_id"]) for it in items if it.get("job_id") is not None})

    calls_by_draft: dict[int, list[dict]] = {}
    if draft_ids:
        c_rows = q(
            conn,
            """SELECT call_id, draft_id, stage, attempt_no, model, prompt_name, status,
                      started_at, finished_at, latency_ms, error_code, created_at
               FROM draft.llm_call_ledger
               WHERE draft_id = ANY(:dids) AND status <> 'cancelled'
               ORDER BY call_id ASC""",
            dids=draft_ids,
        )
        for c in c_rows:
            calls_by_draft.setdefault(int(c["draft_id"]), []).append(c)

    job_map: dict[int, dict] = {}
    if job_ids:
        j_rows = q(
            conn,
            "SELECT job_id, status, error_message, requested_count, created_count, failed_count FROM draft.generation_jobs WHERE job_id = ANY(:jids)",
            jids=job_ids,
        )
        job_map = {int(r["job_id"]): r for r in j_rows}

    now_utc = datetime.now(timezone.utc)
    enriched: list[dict] = []
    for it in items:
        did = int(it["draft_id"])
        st = str(it.get("status") or "pending")
        calls = calls_by_draft.get(did, [])
        job = job_map.get(int(it["job_id"])) if it.get("job_id") is not None else None

        solve_calls = [c for c in calls if c["stage"] == "solve_b"]
        audit_calls = [c for c in calls if c["stage"] in ("checklist_b", "checklist", "audit")]
        running_call = next((c for c in reversed(calls) if c["status"] in ("running", "reserved")), None)
        failed_call = next((c for c in reversed(calls) if c["status"] in ("failed", "timed_out") and c.get("error_code")), None)

        samples_total = samples_k_default
        active_sample = None
        repair_round = 0
        for sc in solve_calls:
            s_no, k_tot, r_no = parse_solve_prompt_tag(sc.get("prompt_name"))
            if k_tot:
                samples_total = k_tot
            if r_no > repair_round:
                repair_round = r_no
            if sc["status"] in ("running", "reserved") and s_no:
                active_sample = s_no

        latest_round_solves = [
            sc for sc in solve_calls
            if parse_solve_prompt_tag(sc.get("prompt_name"))[2] == repair_round
        ] or solve_calls
        samples_done = min(
            samples_total,
            len({parse_solve_prompt_tag(sc.get("prompt_name"))[0] or sc["call_id"] for sc in latest_round_solves if sc["status"] == "succeeded"}),
        )

        if st in ("approved", "needs_human", "rejected"):
            step = 5
        elif running_call and running_call["stage"] in ("checklist_b", "checklist", "audit"):
            step = 5
        elif audit_calls:
            step = 5
        elif running_call and running_call["stage"] == "solve_b":
            step = 3
        elif solve_calls:
            step = 4
        elif st == "reviewing":
            step = 3
        else:
            step = 2

        total_latency_ms = sum(int(c["latency_ms"] or 0) for c in calls if c.get("latency_ms"))
        elapsed_sec: float | None = None
        if running_call and running_call.get("started_at"):
            started = running_call["started_at"]
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            elapsed_sec = round(max(0.1, (now_utc - started).total_seconds()), 1)
        elif total_latency_ms > 0:
            elapsed_sec = round(total_latency_ms / 1000.0, 1)

        raw_model = (
            running_call["model"]
            if running_call
            else (calls[-1]["model"] if calls else it.get("gen_model"))
        )
        fallback_role = "Model A" if step <= 2 else ("Auditor" if step == 5 and audit_calls else "Model B")
        active_model = clean_model_name(raw_model, fallback_role)

        err_alert = format_error_alert(
            (failed_call.get("error_code") if failed_call else None)
            or (job.get("error_message") if job and job.get("status") == "failed" else None)
        )

        enriched.append({
            **it,
            "live_progress": {
                "step": step,
                "total_steps": 5,
                "step_label": "Đang chờ hàng đợi kiểm định..." if (st == "pending" and not running_call) else STEP_LABELS[step],
                "is_running": st in ("pending", "reviewing") or running_call is not None,
                "active_sample": active_sample,
                "samples_done": min(samples_done, samples_total) if samples_done else (samples_total if st == "approved" else 0),
                "samples_total": samples_total,
                "repair_round": repair_round,
                "max_repair_rounds": 2,
                "active_model": active_model,
                "latency_ms": total_latency_ms or None,
                "elapsed_seconds": elapsed_sec,
                "error_alert": err_alert,
            },
        })
    return enriched


def _safe_json(val: Any) -> dict:
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def build_acceptance_dossier(
    conn: Connection,
    draft_row: dict,
    cand: dict,
    validation_report: dict | None,
    runs: list[dict],
    logs: list[dict],
) -> dict:
    status = str(draft_row.get("status") or "pending")
    compare_mode = draft_row.get("compare_mode") or (
        "ordered" if re.search(r"(?i)\b(?:sắp xếp|tăng dần|giảm dần|order\s+by)\b", str(draft_row.get("question") or "")) else "unordered"
    )

    # Trích xuất mã lỗi quyết định từ chu kỳ review mới nhất + status_reason
    dec_idx = [i for i, lg in enumerate(logs) if lg.get("stage") == "decision"]
    cycle_logs = logs[dec_idx[-2] + 1 :] if len(dec_idx) >= 2 else logs
    decision_logs = [lg for lg in cycle_logs if lg.get("stage") == "decision"]
    raw_reason_codes: list[str] = []
    if decision_logs:
        for code in decision_logs[-1].get("reasons") or []:
            if isinstance(code, str) and code.strip():
                raw_reason_codes.append(code.strip())
    st_reason = str(draft_row.get("status_reason") or "").strip()
    if st_reason and not st_reason.startswith("admin_approved") and not st_reason.startswith("PASS_CALIBRATED"):
        for part in [p.strip() for p in st_reason.split(",") if p.strip()]:
            if part not in raw_reason_codes and re.match(r"^[a-z0-9_]+$", part):
                raw_reason_codes.append(part)

    reasons_detail = [
        {"code": code, "explanation": REASON_EXPLANATIONS.get(code, f"Cần kiểm tra điều kiện kỹ thuật ({code}).")}
        for code in dict.fromkeys(raw_reason_codes)
    ]
    if status == "approved":
        reason_summary = "Đạt chuẩn toàn bộ 5/5 công đoạn kiểm định tự động."
    elif reasons_detail:
        reason_summary = "; ".join(f"{r['code']} — {r['explanation']}" for r in reasons_detail)
    elif st_reason:
        reason_summary = st_reason
    elif status in ("pending", "reviewing"):
        reason_summary = "Đang trong hàng đợi thực thi và kiểm định tự động."
    else:
        reason_summary = "Cần Quản trị viên rà soát thủ công trước khi phê duyệt."

    # Khối 2: Chỉ số độc bản & Chống trùng đề (validation_report.duplicate)
    vr = validation_report if isinstance(validation_report, dict) else {}
    dup = vr.get("duplicate") if isinstance(vr.get("duplicate"), dict) else {}
    sim_raw = float(dup.get("similarity") or 0.0)
    sim_pct = round(max(0.0, min(100.0, sim_raw * 100.0)), 1)
    orig_pct = round(max(0.0, 100.0 - sim_pct), 1)
    nearest_id = dup.get("nearest_id") or dup.get("most_similar_id")
    exact_dup = bool(dup.get("exact_duplicate", False))
    logic_dup = bool(dup.get("logic_duplicate", False))
    suspected_dup = bool(dup.get("suspected_duplicate", False) and (exact_dup or logic_dup or sim_raw >= 0.72 or "suspected_duplicate" in raw_reason_codes))

    # Khối 3: Đồng thuận Model B & Bảng ma trận đối chiếu (lấy vòng review mới nhất)
    solve_latencies = q(
        conn,
        """SELECT attempt_no, prompt_name, latency_ms
           FROM draft.llm_call_ledger
           WHERE draft_id = :d AND stage = 'solve_b' AND status = 'succeeded'
           ORDER BY call_id ASC""",
        d=draft_row["draft_id"],
    )
    lat_by_round_sample: dict[tuple[int, int], int] = {}
    fallback_lats: list[int] = []
    for sl in solve_latencies:
        lat = sl.get("latency_ms")
        if lat is not None:
            fallback_lats.append(int(lat))
            s_no, _k, r_no = parse_solve_prompt_tag(sl.get("prompt_name"))
            if s_no is not None:
                lat_by_round_sample[(r_no, s_no - 1)] = int(lat)

    max_round = max((int(r.get("review_round") or 1) for r in runs), default=1)
    latest_runs = [r for r in runs if int(r.get("review_round") or 1) == max_round]
    total_samples = len(latest_runs)
    selected_run = next((r for r in latest_runs if r.get("is_selected")), None)
    target_hash = selected_run.get("result_hash") if selected_run else (
        next((r.get("result_hash") for r in latest_runs if r.get("exec_status") == "ok" and r.get("result_hash")), None)
    )
    matching_count = sum(
        1 for r in latest_runs
        if r.get("exec_status") == "ok" and target_hash and r.get("result_hash") == target_hash
    )
    if status == "approved" and total_samples == 0 and draft_row.get("reference_sql"):
        # Đề seed / tạo sẵn không qua nhiều mẫu solver
        total_samples = 1
        matching_count = 1
    consensus_pct = round((matching_count * 100.0 / total_samples), 1) if total_samples > 0 else 0.0

    latest_r = max((rk for rk, _ in lat_by_round_sample), default=0)
    matrix_samples: list[dict] = []
    for idx, r in enumerate(latest_runs):
        s_idx = int(r.get("sample_index") if r.get("sample_index") is not None else idx)
        lat_ms = lat_by_round_sample.get((latest_r, s_idx))
        if lat_ms is None and idx < len(fallback_lats):
            lat_ms = fallback_lats[idx]
        is_sel = bool(r.get("is_selected"))
        matrix_samples.append({
            "run_id": r.get("run_id"), "sample_label": f"Mẫu {s_idx + 1}", "sample_index": s_idx + 1,
            "model_sql": r.get("model_sql") or "",
            "exec_status": r.get("exec_status") or ("ok" if r.get("row_count") is not None else "error"),
            "latency_ms": lat_ms, "row_count": r.get("row_count"), "result_hash": r.get("result_hash"),
            "error": scrub_legacy_tokens(r.get("error")), "is_selected": is_sel,
            "selection_reason": "Câu ngắn gọn, cấu trúc cây cú pháp AST tối ưu nhất" if is_sel else None,
        })

    # Khối 4: Bảng kiểm toán ngữ nghĩa & Luật bài toán (6 tiêu chí)
    failed_codes = set(raw_reason_codes)
    for lg in cycle_logs:
        if not lg.get("passed"):
            for rc in lg.get("reasons") or []:
                if isinstance(rc, str):
                    failed_codes.add(rc)

    has_positive_rows = (
        any((r.get("row_count") or 0) > 0 for r in latest_runs if r.get("exec_status") == "ok")
        or status == "approved"
    ) and "empty_result" not in failed_codes

    ord_err = bool(failed_codes & {"required_order_by_missing", "order_by_contract_mismatch", "order_disagreement"})
    grain_err = bool(failed_codes & {"one_to_many_join_may_duplicate_output_grain", "tables_mismatch"})
    checklist = [
        {"key": "output_columns", "label": "Khớp cột đầu ra", "passed": "output_columns_mismatch" not in failed_codes,
         "detail": "Tên cột kết quả khớp với yêu cầu đề bài." if "output_columns_mismatch" not in failed_codes else "Tên cột SQL trả về lệch so với cột yêu cầu trong đề."},
        {"key": "unstated_literals", "label": "Không suy diễn điều kiện lạ (Unstated literals)", "passed": "unstated_string_literal" not in failed_codes,
         "detail": "Không tự thêm hằng chuỗi lọc ngoài đề bài." if "unstated_string_literal" not in failed_codes else "Phát hiện hằng chuỗi điều kiện không nêu trong đề bài."},
        {"key": "no_hardcoded_id", "label": "Không gắn cứng ID (No hardcoded ID)", "passed": "hardcoded_id_literal" not in failed_codes,
         "detail": "Không gắn cứng mã định danh số cụ thể trong WHERE." if "hardcoded_id_literal" not in failed_codes else "Phát hiện gắn cứng mã ID cụ thể không có trong đề."},
        {"key": "non_empty_result", "label": "Dữ liệu thực tế khác rỗng (> 0 dòng)", "passed": bool(has_positive_rows),
         "detail": "Kết quả chạy thực tế trên PostgreSQL 17 trả về > 0 dòng." if has_positive_rows else "Kết quả thực thi đang trả về 0 dòng dữ liệu."},
        {"key": "ordering_contract", "label": "Hợp đồng sắp xếp (ORDER BY)", "passed": not ord_err,
         "detail": f"Chế độ {compare_mode}: mệnh đề sắp xếp hợp lệ." if not ord_err else "Thiếu ORDER BY hoặc chiều sắp xếp chưa khớp yêu cầu."},
        {"key": "join_grain", "label": "Quan hệ bảng hợp lệ (Chống nhân bản 1-N)", "passed": not grain_err,
         "detail": "Kết nối khóa ngoại đúng độ mịn bản ghi đầu ra." if not grain_err else "Cần kiểm tra nguy cơ nhân bản dòng khi JOIN 1-N hoặc lệch bảng."},
    ]

    # Khối 5: Lịch sử tự sửa lỗi & Bẫy nghiệp vụ
    repair_info: dict[str, Any] = {"attempted": 0, "limit": 2, "approved_after_repair": False, "rounds": []}
    for lg in cycle_logs:
        raw_obj = _safe_json(lg.get("raw_output"))
        if raw_obj.get("phase") == "repair":
            hist = raw_obj.get("history") if isinstance(raw_obj.get("history"), list) else []
            repair_info = {
                "attempted": int(raw_obj.get("attempted") or len(hist)),
                "limit": int(raw_obj.get("limit") or 2),
                "approved_after_repair": bool(raw_obj.get("approved_after_repair", False)),
                "rounds": [
                    {
                        "round": int(h.get("round") or (i + 1)),
                        "prior_reasons": [
                            {"code": c, "explanation": REASON_EXPLANATIONS.get(c, c)}
                            for c in (h.get("prior_reasons") or [])
                        ],
                        "outcome": h.get("outcome") or "needs_human",
                    }
                    for i, h in enumerate(hist)
                    if isinstance(h, dict)
                ],
            }

    schema_ctx = draft_row.get("schema_context") if isinstance(draft_row.get("schema_context"), dict) else {}
    stored_traps = draft_row.get("traps") if isinstance(draft_row.get("traps"), list) else []
    traps = [str(x).strip() for x in stored_traps if str(x).strip()] or derive_pedagogical_traps(
        {**cand, "question": draft_row.get("question"), "tables_used": draft_row.get("tables_used")},
        schema_ctx,
    )

    return {
        "verdict": {
            "status": status,
            "decision_passed": status == "approved",
            "reason_summary": reason_summary,
            "reasons": reasons_detail,
            "compare_mode": compare_mode,
        },
        "originality": {
            "similarity_pct": sim_pct,
            "originality_pct": orig_pct,
            "nearest_id": nearest_id,
            "exact_duplicate": exact_dup,
            "logic_duplicate": logic_dup,
            "suspected_duplicate": suspected_dup,
        },
        "consensus": {
            "matching_count": matching_count,
            "total_samples": total_samples,
            "consensus_pct": consensus_pct,
            "review_round": max_round,
            "samples": matrix_samples,
        },
        "checklist": checklist,
        "repair_and_traps": {
            "repair_history": repair_info,
            "traps": traps,
        },
    }
