"""Nạp dữ liệu Core (world Enterprise, 6 skill S1–S6, 50 đề nguồn) từ seed/core_seed.json. Chạy lặp an toàn."""
import json

from sqlalchemy import Connection

from .config import get_settings
from .db import ex, q1
from .domain import DIFF_NUM
from .services import settings_registry


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def seed_core(conn: Connection) -> dict:
    data = json.loads(get_settings().seed_path.read_text(encoding="utf-8"))
    w = data["worlds"][0]
    ex(conn, """INSERT INTO core.worlds (name, display_name, schema_description, fk_relations, business_rules, planted_traps,
                allowed_sql_features, dataset_ref, variant_count, dataset_version)
                VALUES (:n, :d, CAST(:sd AS jsonb), CAST(:fk AS jsonb), CAST(:br AS jsonb), CAST(:pt AS jsonb), CAST(:al AS jsonb),
                        'enterprise', 0, 1) ON CONFLICT (name) DO NOTHING""",
       n=w["world_id"], d=w["name"], sd=_j(w["schema_description"]), fk=_j(w["fk_relations"]),
       br=_j(w["business_rules"]), pt=_j(w["planted_traps"]), al=_j(w["allowed_sql_features"]))
    world_pk = q1(conn, "SELECT world_id FROM core.worlds WHERE name=:n", n=w["world_id"])["world_id"]
    for s in data["skills"]:
        ex(conn, """INSERT INTO core.skills (code, name, category, base_difficulty) VALUES (:c, :n, :cat, :bd)
                    ON CONFLICT (code) DO NOTHING""", c=s["skill_id"], n=s["name"], cat=s["category"], bd=DIFF_NUM[s["base_difficulty"]])
    skill_pk = {r["code"]: r["skill_id"] for r in conn.exec_driver_sql("SELECT code, skill_id FROM core.skills").mappings()}
    inserted = 0
    for s in data["source_questions"]:
        inserted += ex(conn, """INSERT INTO core.source_questions (code, world_id, title, question_text, reference_sql, difficulty,
                    primary_skill_id, primary_business_domain, skills, depth, metadata, validation)
                    VALUES (:c, :w, :t, :qt, :rsql, :d, :sk, :dom, CAST(:skills AS jsonb), :depth, CAST(:m AS jsonb), CAST(:v AS jsonb))
                    ON CONFLICT (code) DO NOTHING""",
                       c=s["question_id"], w=world_pk, t=s["title"], qt=s["question_text"], rsql=s["reference_sql"],
                       d=DIFF_NUM[s["difficulty"]], sk=skill_pk[s["primary_skill_group"]], dom=s["primary_business_domain"],
                       skills=_j(s["skills"]), depth=s["depth"], m=_j(s["metadata"]), v=_j(s["validation"]))
    settings_registry.ensure_defaults(conn)
    return {"world_id": world_pk, "skills": len(skill_pk), "source_questions_inserted": inserted}


def seed_demo_live(conn: Connection) -> dict:
    """Khởi tạo dữ liệu live demo (users, live.questions, test_cases, weekly_sets, drafts, submissions)."""
    from datetime import date, timedelta
    from .services import auth, submissions
    core_info = seed_core(conn)
    world_pk = core_info["world_id"]
    admin_role = q1(conn, "SELECT role_id FROM live.roles WHERE name='admin'")["role_id"]
    learner_role = q1(conn, "SELECT role_id FROM live.roles WHERE name='learner'")["role_id"]

    demo_users = [
        (admin_role, "admin@sqlarena.local", "admin", "admin123", "Nguyễn Quản Trị (Admin)", "Project Lead & AI Pipeline Reviewer"),
        (learner_role, "learner@sqlarena.local", "nguyen_ptit", "demo123", "Bình Nguyên (PTIT)", "Sinh viên CNTT PTIT — Data & Backend Engineering"),
        (learner_role, "tuanle@sqlarena.local", "tuan_le", "demo123", "Lê Minh Tuấn", "Data Analyst — SQL Specialist"),
        (learner_role, "hanguyen@sqlarena.local", "ha_nguyen", "demo123", "Nguyễn Thu Hà", "BI Developer"),
        (learner_role, "minhpham@sqlarena.local", "minh_pham", "demo123", "Phạm Hoàng Minh", "Backend Engineer"),
    ]
    user_ids = {}
    for rid, email, uname, pwd, dname, bio in demo_users:
        r = q1(conn, """INSERT INTO live.users (role_id, email, username, password_hash, display_name, bio, status)
                        VALUES (:r, :e, :u, :p, :d, :b, 'active')
                        ON CONFLICT ((lower(email))) DO UPDATE SET password_hash=EXCLUDED.password_hash, display_name=EXCLUDED.display_name
                        RETURNING user_id""",
               r=rid, e=email, u=uname, p=auth.hash_password(pwd), d=dname, b=bio)
        user_ids[uname] = r["user_id"]

    # Promote 50 source questions -> live.questions + live.test_cases if not yet promoted
    existing_q = q1(conn, "SELECT count(*) AS n FROM live.questions")["n"]
    if existing_q == 0:
        srcs = conn.exec_driver_sql("SELECT * FROM core.source_questions ORDER BY source_id").mappings().all()
        for sq in srcs:
            meta = sq["metadata"] or {}
            tables = meta.get("tables_used") or []
            mode = "ordered" if meta.get("ordering_required", True) else "unordered"
            schema_txt = f"-- Bảng sử dụng: {', '.join(tables)}\n-- Mục tiêu: {meta.get('business_goal', '')}"
            qrow = q1(conn, """INSERT INTO live.questions
                               (world_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, tables_used, schema_text, status, is_source, pass_rate)
                               VALUES (:w, :t, :q, :sql, :m, :d, :sk, :tu, :st, 'ready', true, :pr)
                               RETURNING question_id""",
                      w=world_pk, t=sq["title"], q=sq["question_text"], sql=sq["reference_sql"],
                      m=mode, d=sq["difficulty"], sk=[sq["primary_skill_id"]], tu=tables, st=schema_txt,
                      pr=round(88.0 - sq["difficulty"] * 12.5, 1))
            qid = qrow["question_id"]
            res = submissions.execute_sandbox_sql(sq["reference_sql"])
            exp = {"columns": res.get("columns", []), "rows": res.get("rows", []), "row_count": res.get("row_count", 0), "compare_mode": mode}
            ex(conn, """INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result, is_hidden)
                        VALUES (:q, 'enterprise/base', 1, 'standard', CAST(:e AS jsonb), false) ON CONFLICT DO NOTHING""",
               q=qid, e=_j(exp))

    # Create published weekly set if none exists
    pub = q1(conn, "SELECT set_id FROM live.weekly_sets WHERE status='published'")
    if not pub:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        ws = q1(conn, """INSERT INTO live.weekly_sets (title, week_start, status, published_at)
                         VALUES ('Tuần #42 — Thử thách SQL Doanh nghiệp (Enterprise DB)', :ws, 'published', now())
                         ON CONFLICT (week_start) DO UPDATE SET status='published', published_at=now()
                         RETURNING set_id""", ws=monday)
        set_id = ws["set_id"]
        q_easy = [r["question_id"] for r in conn.exec_driver_sql("SELECT question_id FROM live.questions WHERE difficulty=1 ORDER BY question_id LIMIT 5").mappings()]
        q_med = [r["question_id"] for r in conn.exec_driver_sql("SELECT question_id FROM live.questions WHERE difficulty=2 ORDER BY question_id LIMIT 10").mappings()]
        q_hard = [r["question_id"] for r in conn.exec_driver_sql("SELECT question_id FROM live.questions WHERE difficulty=3 ORDER BY question_id LIMIT 5").mappings()]
        for pos, qid in enumerate(q_easy + q_med + q_hard, start=1):
            ex(conn, """INSERT INTO live.weekly_set_items (set_id, question_id, position, is_voided)
                        VALUES (:s, :q, :p, false) ON CONFLICT DO NOTHING""", s=set_id, q=qid, p=pos)

    # Seed sample AI generation job + drafts + submissions if empty
    if q1(conn, "SELECT count(*) AS n FROM draft.generation_jobs")["n"] == 0:
        job = q1(conn, """INSERT INTO draft.generation_jobs
                          (world_id, triggered_by, difficulty, skill_ids, topic, requested_count, created_count, failed_count, status, started_at, finished_at)
                          VALUES (:w, :u, 2, ARRAY[2,3,5], 'Phân tích doanh thu & giữ chân khách hàng B2B', 4, 4, 0, 'done', now() - interval '15 minutes', now() - interval '12 minutes')
                          RETURNING job_id""", w=world_pk, u=user_ids["admin"])
        jid = job["job_id"]
        sample_drafts = [
            ("Top 5 danh mục có tỷ lệ hoàn tiền cao nhất quý 1/2025",
             "Viết truy vấn tìm 5 danh mục sản phẩm có tổng giá trị hoàn tiền (refunds.amount) cao nhất trong quý 1 năm 2025. Trả về category_id, category_name, total_refund_amount, sắp xếp giảm dần theo total_refund_amount.",
             "SELECT c.category_id, c.category_name, COALESCE(SUM(rf.amount), 0) AS total_refund_amount FROM categories c JOIN products p ON p.category_id = c.category_id JOIN order_items oi ON oi.product_id = p.product_id JOIN refunds rf ON rf.order_id = oi.order_id WHERE rf.created_at >= '2025-01-01' AND rf.created_at < '2025-04-01' GROUP BY c.category_id, c.category_name ORDER BY total_refund_amount DESC, c.category_id ASC LIMIT 5",
             2, [2, 3], ["categories", "products", "order_items", "refunds"], "needs_human", "CONSENSUS_WEAK: 2/3 lời giải Model B khớp hash trên mutant dataset, cần Admin xác nhận tie-breaker."),
            ("Nhân viên vượt KPI doanh số trung bình của phòng ban",
             "Liệt kê các nhân viên có tổng doanh số đơn hàng hoàn thành (orders.status = 'completed') lớn hơn mức doanh số trung bình của các nhân viên trong cùng phòng ban. Trả về employee_id, full_name, department_id, total_sales.",
             "WITH emp_sales AS (SELECT e.employee_id, e.full_name, e.department_id, COALESCE(SUM(o.total_amount), 0) AS total_sales FROM employees e LEFT JOIN orders o ON o.employee_id = e.employee_id AND o.status = 'completed' GROUP BY e.employee_id, e.full_name, e.department_id), dept_avg AS (SELECT department_id, AVG(total_sales) AS avg_sales FROM emp_sales GROUP BY department_id) SELECT s.employee_id, s.full_name, s.department_id, s.total_sales FROM emp_sales s JOIN dept_avg d ON d.department_id = s.department_id WHERE s.total_sales > d.avg_sales ORDER BY s.total_sales DESC, s.employee_id ASC",
             3, [4, 5], ["employees", "orders"], "needs_human", "SEMANTIC_WARNING: Cần Admin xác nhận nhân viên có 0 đơn hàng có tính vào trung bình phòng ban hay không."),
            ("Thống kê khách hàng VIP có từ 3 đơn hàng đã thanh toán",
             "Tìm các khách hàng có ít nhất 3 đơn hàng ở trạng thái 'completed'. Trả về customer_id, full_name, completed_order_count, total_spent, sắp xếp giảm dần theo total_spent.",
             "SELECT c.customer_id, c.full_name, COUNT(o.order_id) AS completed_order_count, SUM(o.total_amount) AS total_spent FROM customers c JOIN orders o ON o.customer_id = c.customer_id WHERE o.status = 'completed' GROUP BY c.customer_id, c.full_name HAVING COUNT(o.order_id) >= 3 ORDER BY total_spent DESC, c.customer_id ASC",
             1, [2, 3], ["customers", "orders"], "approved", "PASS_ALL_7_GATES: Vượt qua 3/3 self-solve consensus & semantic audit."),
        ]
        for title, qtxt, rsql, diff, sks, tbls, st, reason in sample_drafts:
            bp = {"candidate": {"business_domain": "sales_analytics", "business_goal": title, "difficulty_reason": reason, "output_columns": ["id", "total"]}, "source_question_ids": [1, 2]}
            vr = {"passed": st == "approved", "consensus": "3/3" if st == "approved" else "2/3", "reason": reason}
            drow = q1(conn, """INSERT INTO draft.question_drafts
                               (world_id, job_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, blueprint, tables_used, schema_text, validation_report, status, status_reason, gen_model, gen_prompt_version, review_attempts)
                               VALUES (:w, :j, :t, :q, :sql, 'ordered', :d, :sk, CAST(:bp AS jsonb), :tu, :stxt, CAST(:vr AS jsonb), :st, :r, 'qwen2.5-coder:14b', 'v2.4-ct', 1)
                               RETURNING draft_id""",
                      w=world_pk, j=jid, t=title, q=qtxt, sql=rsql, d=diff, sk=sks, bp=_j(bp), tu=tbls,
                      stxt=f"-- Tables: {', '.join(tbls)}", vr=_j(vr), st=st, r=reason)
            did = drow["draft_id"]
            ex(conn, """INSERT INTO draft.self_solve_runs (draft_id, sample_index, model_sql, is_selected, matched_datasets, total_datasets, exec_status, row_count, review_model, review_round)
                        VALUES (:d, 0, :sql, true, 3, 3, 'ok', 5, 'deepseek-coder-v2:16b', 1)""", d=did, sql=rsql)
            ex(conn, """INSERT INTO draft.review_logs (draft_id, stage, passed, score, reasons, review_model, rubric_version)
                        VALUES (:d, 'decision', :p, :sc, CAST(:rs AS jsonb), 'deepseek-coder-v2:16b', 'rubric-v7')""",
               d=did, p=(st == "approved"), sc=(95.0 if st == "approved" else 78.5), rs=_j([reason]))

    if q1(conn, "SELECT count(*) AS n FROM live.submissions")["n"] == 0:
        pub_set = q1(conn, "SELECT set_id FROM live.weekly_sets WHERE status='published'")
        sid = pub_set["set_id"] if pub_set else None
        qs = conn.exec_driver_sql("SELECT question_id, reference_sql FROM live.questions ORDER BY question_id LIMIT 12").mappings().all()
        learners = [(user_ids["tuan_le"], 10, 95), (user_ids["nguyen_ptit"], 8, 112), (user_ids["ha_nguyen"], 6, 134), (user_ids["minh_pham"], 4, 160)]
        for uid, solved_n, base_ms in learners:
            for idx, qrow in enumerate(qs[:solved_n]):
                ex(conn, """INSERT INTO live.submissions (user_id, question_id, set_id, submitted_sql, submission_status, execution_status, score, runtime_ms)
                            VALUES (:u, :q, :s, :sql, 'passed', 'passed', 100.0, :ms)""",
                   u=uid, q=qrow["question_id"], s=sid, sql=qrow["reference_sql"], ms=base_ms + idx * 9)

    return {"users": len(user_ids), "questions": q1(conn, "SELECT count(*) AS n FROM live.questions")["n"]}
