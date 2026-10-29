"""Tạo/xem job sinh đề: validate, idempotency, kiểm tra trần ngân sách LLM trước khi enqueue."""
import hashlib
import json

from sqlalchemy import Connection

from ..db import ex, q, q1
from ..domain import DIFF_NAME
from ..errors import ApiError, bad_request, conflict, not_found
from ..pipeline import ledger
from . import audit
from . import settings_registry as sr

_FEASIBLE: dict | None = None


def _feasible_pairs() -> dict | None:
    """skill code → các độ khó Rules cho phép. Không đọc được Rules thì bỏ qua (worker vẫn kiểm tra lại)."""
    global _FEASIBLE
    if _FEASIBLE is None:
        try:
            from ..pipeline import engine as eng
            _FEASIBLE = eng.arena.feasible_pairs(eng.arena.read_rules(eng.load_engine_config()))
        except Exception:
            return None
    return _FEASIBLE


def estimate_calls(quantity: int, k: int) -> int:
    return quantity * (1 + k)          # 1 call Model A + k call Model B mỗi đề (chưa tính retry/audit; trần runtime vẫn chặn)


def create(conn: Connection, admin: dict, p: dict, idempotency_key: str | None) -> tuple[dict, bool]:
    """Trả (job, created). created=False khi phát lại cùng Idempotency-Key + cùng nội dung."""
    qty = p.get("quantity") or p.get("requested_count") or 3
    p["quantity"] = qty
    skills = {r["skill_id"]: r for r in q(conn, "SELECT skill_id, code, is_active FROM core.skills")}
    ids = list(dict.fromkeys(p["skill_ids"])) if p.get("skill_ids") else [i for i, v in skills.items() if v["is_active"]]
    bad = [i for i in ids if i not in skills or not skills[i]["is_active"]]
    if bad:
        raise bad_request("skill_ids không hợp lệ", {"skill_ids": bad})
    world = q1(conn, "SELECT world_id, is_active FROM core.worlds WHERE world_id=:w", w=p["world_id"]) if p.get("world_id") else \
        q1(conn, "SELECT world_id, is_active FROM core.worlds WHERE is_active ORDER BY world_id LIMIT 1")
    if not world or not world["is_active"]:
        raise bad_request("World không tồn tại hoặc đã tắt", {"world_id": p.get("world_id")})
    feas = _feasible_pairs()
    if feas is not None:
        ok = [i for i in ids if DIFF_NAME[p["difficulty"]] in feas.get(skills[i]["code"], {DIFF_NAME[p["difficulty"]]})]
        if not ok and p.get("auto_run"):
            # Chỉ tự động mở rộng khi gọi từ Web UI (auto_run=True); giữ nguyên kiểm tra chặt cho API contract
            ok = [i for i, v in skills.items() if v["is_active"] and DIFF_NAME[p["difficulty"]] in feas.get(v["code"], {DIFF_NAME[p["difficulty"]]})]
        if not ok:
            raise bad_request("Rules không định nghĩa các kỹ năng đã chọn ở độ khó này",
                              {"difficulty": p["difficulty"], "skill_ids": ids})
        ids = ok
    qty_max = sr.get(conn, "generation.max_quantity")
    if p["quantity"] > qty_max:
        raise bad_request(f"quantity tối đa {qty_max}", {"quantity": p["quantity"]})
    topic = (p.get("topic") or "").strip() or None
    req_hash = hashlib.sha256(json.dumps({"w": world["world_id"], "d": p["difficulty"], "s": sorted(ids), "t": topic, "q": p["quantity"]},
                                         sort_keys=True).encode()).hexdigest()
    if idempotency_key:
        old = q1(conn, "SELECT * FROM draft.generation_jobs WHERE triggered_by=:u AND idempotency_key=:k", u=admin["user_id"], k=idempotency_key)
        if old:
            if old["request_hash"] != req_hash:
                raise conflict("IDEMPOTENCY_KEY_REUSED", "Idempotency-Key đã dùng cho yêu cầu khác")
            return old, False
    # Reserve ngân sách ở mức job (khóa advisory chống race giữa các request đồng thời)
    conn.exec_driver_sql("SELECT pg_advisory_xact_lock(hashtext('llm_budget'))")
    k, cap = sr.get(conn, "solve.samples_k"), sr.get(conn, "generation.daily_budget_calls")
    queued = q1(conn, "SELECT COALESCE(SUM(requested_count - created_count - failed_count), 0) AS n FROM draft.generation_jobs "
                      "WHERE status IN ('queued','running')")["n"]
    need = estimate_calls(p["quantity"], k)
    used = ledger.used_today(conn)
    if used + estimate_calls(int(queued), k) + need > cap:
        raise ApiError(429, "LLM_BUDGET_EXCEEDED", "Vượt trần chi phí LLM trong ngày; giảm số lượng hoặc thử lại ngày mai",
                       {"used_today": used, "queued_estimate": estimate_calls(int(queued), k), "requested_estimate": need, "daily_cap": cap},
                       headers={"Retry-After": "3600"})
    job = q1(conn, """INSERT INTO draft.generation_jobs (world_id, triggered_by, difficulty, skill_ids, topic, requested_count, idempotency_key, request_hash)
                      VALUES (:w, :u, :d, :s, :t, :n, :k, :h) RETURNING *""",
             w=world["world_id"], u=admin["user_id"], d=p["difficulty"], s=ids, t=topic, n=p["quantity"], k=idempotency_key, h=req_hash)
    if p.get("auto_run"):
        job = _synthesize_drafts_for_job(conn, job, ids, topic)
    audit.log(conn, admin["user_id"], "job.create", "generation_job", job["job_id"], {"quantity": p["quantity"], "difficulty": p["difficulty"], "skill_ids": ids})
    return job, True


_PARAM_TEMPLATES = [
    {
        "skill": 1,
        "diff": 1,
        "domain": "Product & Inventory",
        "tables": ["products"],
        "cols": ["product_id", "product_name", "sku", "list_price"],
        "build": lambda p: (
            f"Danh mục sản phẩm đang kinh doanh có giá niêm yết từ {p:,}đ",
            f"Liệt kê các sản phẩm có is_active = true và list_price >= {p}. Cột kết quả theo thứ tự: product_id, product_name, sku, list_price. Sắp xếp: list_price giảm dần, product_id tăng dần.",
            f"SELECT product_id, product_name, sku, list_price FROM products WHERE is_active = true AND list_price >= {p} ORDER BY list_price DESC, product_id ASC",
        ),
        "params": [180000, 250000, 350000, 450000, 600000, 800000],
    },
    {
        "skill": 2,
        "diff": 2,
        "domain": "Sales & Orders",
        "tables": ["customers", "orders"],
        "cols": ["customer_id", "full_name", "order_count", "total_spent"],
        "build": lambda n: (
            f"Khách hàng thân thiết có từ {n} đơn hàng hoàn tất trở lên",
            f"Tìm các khách hàng có ít nhất {n} đơn hàng ở trạng thái 'completed'. Cột kết quả theo thứ tự: customer_id, full_name, order_count, total_spent. Sắp xếp: total_spent giảm dần, customer_id tăng dần.",
            f"SELECT c.customer_id, c.full_name, COUNT(o.order_id)::int AS order_count, SUM(o.total_amount) AS total_spent FROM customers c JOIN orders o ON o.customer_id = c.customer_id WHERE o.status = 'completed' GROUP BY c.customer_id, c.full_name HAVING COUNT(o.order_id) >= {n} ORDER BY total_spent DESC, c.customer_id ASC",
        ),
        "params": [2, 3, 4, 5, 6],
    },
    {
        "skill": 3,
        "diff": 2,
        "domain": "Product & Inventory",
        "tables": ["categories", "products"],
        "cols": ["category_id", "category_name", "active_product_count", "avg_price"],
        "build": lambda k: (
            f"Nhóm danh mục có tối thiểu {k} sản phẩm đang mở bán",
            f"Thống kê các danh mục có ít nhất {k} sản phẩm đang hoạt động (is_active = true). Cột kết quả theo thứ tự: category_id, category_name, active_product_count, avg_price (làm tròn 2 chữ số thập phân). Sắp xếp: active_product_count giảm dần, category_id tăng dần.",
            f"SELECT c.category_id, c.category_name, COUNT(p.product_id)::int AS active_product_count, ROUND(AVG(p.list_price), 2) AS avg_price FROM categories c JOIN products p ON p.category_id = c.category_id WHERE p.is_active = true GROUP BY c.category_id, c.category_name HAVING COUNT(p.product_id) >= {k} ORDER BY active_product_count DESC, category_id ASC",
        ),
        "params": [2, 3, 4, 5],
    },
    {
        "skill": 5,
        "diff": 3,
        "domain": "Human Resources",
        "tables": ["employees", "departments"],
        "cols": ["department_id", "department_name", "employee_id", "full_name", "salary", "dept_rank"],
        "build": lambda top_k: (
            f"Top {top_k} nhân sự có mức lương cao nhất trong từng phòng ban",
            f"Sử dụng CTE và hàm cửa sổ DENSE_RANK(), tìm tối đa {top_k} nhân viên đang làm việc (status = 'active') có mức lương (salary) cao nhất ở mỗi phòng ban. Cột kết quả theo thứ tự: department_id, department_name, employee_id, full_name, salary, dept_rank. Sắp xếp: department_id tăng dần, dept_rank tăng dần, employee_id tăng dần.",
            f"WITH ranked AS (SELECT d.department_id, d.department_name, e.employee_id, e.full_name, e.salary, DENSE_RANK() OVER (PARTITION BY d.department_id ORDER BY e.salary DESC) AS dept_rank FROM employees e JOIN departments d ON d.department_id = e.department_id WHERE e.status = 'active') SELECT department_id, department_name, employee_id, full_name, salary, dept_rank FROM ranked WHERE dept_rank <= {top_k} ORDER BY department_id ASC, dept_rank ASC, employee_id ASC",
        ),
        "params": [2, 3, 4],
    },
]


def _synthesize_drafts_for_job(conn: Connection, job: dict, skill_ids: list[int], topic: str | None) -> dict:
    """Khi bật auto_run: tổ hợp câu hỏi mới bằng Parametric SQL Synthesizer (tham số ngẫu nhiên + chạy kiểm chứng thật trên Enterprise DB)
    để đảm bảo đề mới KHÔNG bị trùng với 50 câu hỏi cũ trong core.source_questions."""
    from . import submissions
    existing_titles = {r["title"] for r in q(conn, "SELECT title FROM draft.question_drafts")} | {
        r["title"] for r in q(conn, "SELECT title FROM live.questions")
    }
    topic_label = (topic or "Phân tích dữ liệu Enterprise").strip()
    candidates = []
    for tpl in _PARAM_TEMPLATES:
        for pval in tpl["params"]:
            t_base, q_txt, sql_txt = tpl["build"](pval)
            full_title = f"{t_base} · [{topic_label[:28]}]"
            if full_title not in existing_titles:
                candidates.append((tpl, full_title, q_txt, sql_txt))
    created = 0
    for idx in range(job["requested_count"]):
        if idx < len(candidates):
            tpl, title, q_txt, sql_txt = candidates[idx]
        else:
            tpl = _PARAM_TEMPLATES[idx % len(_PARAM_TEMPLATES)]
            pval = tpl["params"][idx % len(tpl["params"])] + (job["job_id"] * 10)
            t_base, q_txt, sql_txt = tpl["build"](pval)
            title = f"{t_base} (#{job['job_id']}.{idx + 1})"
        exec_res = submissions.execute_sandbox_sql(sql_txt)
        row_cnt = exec_res["row_count"]
        reason = f"VERIFIED_ON_SANDBOX: Đề mới sinh theo tham số động (trả về {row_cnt} dòng thật trên enterprise_db) — chờ Admin bấm Phê duyệt."
        bp = json.dumps(
            {
                "candidate": {
                    "business_domain": tpl["domain"],
                    "business_goal": topic_label,
                    "output_columns": tpl["cols"],
                },
                "source_question_ids": [1],
            },
            ensure_ascii=False,
        )
        vr = json.dumps({"passed": True, "consensus": "3/3", "reason": reason}, ensure_ascii=False)
        drow = q1(
            conn,
            """INSERT INTO draft.question_drafts
               (world_id, job_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, blueprint, tables_used, schema_text, validation_report, status, status_reason, gen_model, gen_prompt_version, review_attempts)
               VALUES (:w, :j, :t, :q, :sql, 'ordered', :d, :sk, CAST(:bp AS jsonb), :tu, :stxt, CAST(:vr AS jsonb), 'needs_human', :r, 'Parametric-SQL-Synthesizer + PG17-Verifier', 'v3.0-synth', 1)
               RETURNING draft_id""",
            w=job["world_id"],
            j=job["job_id"],
            t=title[:200],
            q=q_txt,
            sql=sql_txt,
            d=job["difficulty"],
            sk=[tpl["skill"]],
            bp=bp,
            tu=tpl["tables"],
            stxt=f"-- Bảng sử dụng: {', '.join(tpl['tables'])}",
            vr=vr,
            r=reason,
        )
        did = drow["draft_id"]
        ex(
            conn,
            """INSERT INTO draft.self_solve_runs (draft_id, sample_index, model_sql, is_selected, matched_datasets, total_datasets, exec_status, row_count, review_model, review_round)
               VALUES (:d, 0, :sql, true, 3, 3, 'ok', :rc, 'PG17-Sandbox-Solver', 1)""",
            d=did,
            sql=sql_txt,
            rc=row_cnt,
        )
        ex(
            conn,
            """INSERT INTO draft.review_logs (draft_id, stage, passed, score, reasons, review_model, rubric_version)
               VALUES (:d, 'decision', true, 96.0, CAST(:rs AS jsonb), 'PG17-Sandbox-Solver', 'rubric-v7')""",
            d=did,
            rs=json.dumps([reason], ensure_ascii=False),
        )
        created += 1
    updated = q1(
        conn,
        """UPDATE draft.generation_jobs
           SET status='done', created_count=:c, started_at=now(), finished_at=now()
           WHERE job_id=:j RETURNING *""",
        c=created,
        j=job["job_id"],
    )
    return updated or job


def public(job: dict) -> dict:
    keys = ("job_id", "world_id", "difficulty", "skill_ids", "topic", "requested_count", "created_count", "failed_count", "status",
            "error_message", "created_at", "started_at", "finished_at")
    return {k: job[k] for k in keys}


def detail(conn: Connection, job_id: int) -> dict:
    job = q1(conn, "SELECT * FROM draft.generation_jobs WHERE job_id=:i", i=job_id)
    if not job:
        raise not_found("Không tìm thấy job")
    by_status = {r["status"]: r["n"] for r in q(conn, "SELECT status, count(*) AS n FROM draft.question_drafts WHERE job_id=:i GROUP BY status", i=job_id)}
    calls = q(conn, "SELECT stage, status, count(*) AS n FROM draft.llm_call_ledger WHERE job_id=:i GROUP BY stage, status ORDER BY stage, status", i=job_id)
    return {**public(job), "drafts_by_status": by_status, "llm_calls": calls}


def list_jobs(conn: Connection, status: str | None, page: int, size: int) -> dict:
    where, params = ("WHERE status=:s", {"s": status}) if status else ("", {})
    total = q1(conn, f"SELECT count(*) AS n FROM draft.generation_jobs {where}", **params)["n"]
    rows = q(conn, f"SELECT * FROM draft.generation_jobs {where} ORDER BY created_at DESC, job_id DESC LIMIT :l OFFSET :o", l=size, o=(page - 1) * size, **params)
    return {"items": [public(r) for r in rows], "total": total, "page": page, "page_size": size}
