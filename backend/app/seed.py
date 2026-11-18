"""Nạp dữ liệu khởi tạo thực tế (world Enterprise, 6 kỹ năng S1–S6, 50 đề nguồn & dữ liệu vận hành thực thi trực tiếp trên PostgreSQL 17)."""
import hashlib
import json
import os
from datetime import date, timedelta

from sqlalchemy import Connection

from .config import get_settings
from .db import ex, q, q1
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
    """Khởi tạo dữ liệu thực tế cho môi trường mới git clone (mọi truy vấn & test case đều thực thi thật trên enterprise_db)."""
    from .services import auth, promotion, submissions

    core_info = seed_core(conn)
    world_pk = core_info["world_id"]
    admin_role = q1(conn, "SELECT role_id FROM live.roles WHERE name='admin'")["role_id"]
    learner_role = q1(conn, "SELECT role_id FROM live.roles WHERE name='learner'")["role_id"]

    admin_uname = os.environ.get("SEED_ADMIN_USERNAME", "admin").strip() or "admin"
    admin_pwd = os.environ.get("SEED_ADMIN_PASSWORD", "admin123")
    admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@ptit.edu.vn").strip()
    learner_uname = os.environ.get("SEED_LEARNER_USERNAME", "hocvien").strip() or "hocvien"
    learner_pwd = os.environ.get("SEED_LEARNER_PASSWORD", "hocvien123")
    learner_email = os.environ.get("SEED_LEARNER_EMAIL", "hocvien@stu.ptit.edu.vn").strip()

    seed_accounts = [
        (admin_role, admin_email, admin_uname, admin_pwd, "Quản trị viên Hệ thống (PTIT)", "Giảng viên phụ trách & Kiểm duyệt Ngân hàng đề SQL"),
        (learner_role, learner_email, learner_uname, learner_pwd, "Nguyễn Minh Khôi", "Sinh viên CNTT PTIT — Thực hành Cơ sở dữ liệu"),
        (learner_role, "nguyen.b22@stu.ptit.edu.vn", "nguyen_b22", "ptit2026", "Trần Bình Nguyên", "Sinh viên B22DCCN — Kỹ thuật Phần mềm"),
        (learner_role, "tuan.b22@stu.ptit.edu.vn", "tuan_b22", "ptit2026", "Lê Minh Tuấn", "Sinh viên B22DCCN — Hệ thống Thông tin"),
        (learner_role, "ha.b22@stu.ptit.edu.vn", "ha_b22", "ptit2026", "Nguyễn Thu Hà", "Sinh viên B22DCAT — An toàn Thông tin"),
    ]
    user_ids: dict[str, int] = {}
    for rid, email, uname, pwd, dname, bio in seed_accounts:
        found = q1(
            conn,
            "SELECT user_id, password_hash FROM live.users WHERE lower(email)=lower(:e) OR lower(username)=lower(:u) ORDER BY (lower(username)=lower(:u)) DESC LIMIT 1",
            e=email,
            u=uname,
        )
        if found:
            user_ids[uname] = found["user_id"]
            if not str(found.get("password_hash") or "").startswith("pbkdf2_sha256$"):
                ex(conn, "UPDATE live.users SET password_hash=:p WHERE user_id=:id", p=auth.hash_password(pwd), id=found["user_id"])
        else:
            r = q1(
                conn,
                """INSERT INTO live.users (role_id, email, username, password_hash, display_name, bio, status)
                   VALUES (:r, :e, :u, :p, :d, :b, 'active')
                   RETURNING user_id""",
                r=rid,
                e=email,
                u=uname,
                p=auth.hash_password(pwd),
                d=dname,
                b=bio,
            )
            user_ids[uname] = r["user_id"]

    # Thực thi thật 50 đề nguồn trên enterprise_db để tạo live.questions + live.test_cases chuẩn xác 100%
    existing_q = q1(conn, "SELECT count(*) AS n FROM live.questions")["n"]
    if existing_q == 0:
        srcs = conn.exec_driver_sql("SELECT * FROM core.source_questions ORDER BY source_id").mappings().all()
        for sq in srcs:
            meta = sq["metadata"] or {}
            tables = meta.get("tables_used") or []
            mode = "ordered" if meta.get("ordering_required", True) else "unordered"
            schema_txt = f"-- Bảng sử dụng: {', '.join(tables)}\n-- Mục tiêu: {meta.get('business_goal', '')}"
            res = submissions.execute_sandbox_sql(sq["reference_sql"])
            qrow = q1(
                conn,
                """INSERT INTO live.questions
                   (world_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, tables_used, schema_text, status, is_source, pass_rate)
                   VALUES (:w, :t, :q, :sql, :m, :d, :sk, :tu, :st, 'ready', true, 0.0)
                   RETURNING question_id""",
                w=world_pk,
                t=sq["title"],
                q=sq["question_text"],
                sql=sq["reference_sql"],
                m=mode,
                d=sq["difficulty"],
                sk=[sq["primary_skill_id"]],
                tu=tables,
                st=schema_txt,
            )
            qid = qrow["question_id"]
            exp = {
                "columns": res.get("columns", []),
                "rows": res.get("rows", []),
                "row_count": res.get("row_count", 0),
                "compare_mode": mode,
            }
            ex(
                conn,
                """INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result, is_hidden)
                   VALUES (:q, 'enterprise/base', 1, 'standard', CAST(:e AS jsonb), false) ON CONFLICT DO NOTHING""",
                q=qid,
                e=_j(exp),
            )

    # Tạo bộ đề tuần đang mở từ ngân hàng câu hỏi thực tế nếu chưa có
    pub = q1(conn, "SELECT set_id FROM live.weekly_sets WHERE status='published'")
    if not pub:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        ws = q1(
            conn,
            """INSERT INTO live.weekly_sets (title, week_start, status, published_at)
               VALUES ('Bộ đề Thực hành SQL Doanh nghiệp (PostgreSQL 17)', :ws, 'published', now())
               ON CONFLICT (week_start) DO UPDATE SET status='published', published_at=now()
               RETURNING set_id""",
            ws=monday,
        )
        set_id = ws["set_id"]
        q_easy = [r["question_id"] for r in conn.exec_driver_sql("SELECT question_id FROM live.questions WHERE difficulty=1 AND status='ready' ORDER BY question_id LIMIT 5").mappings()]
        q_med = [r["question_id"] for r in conn.exec_driver_sql("SELECT question_id FROM live.questions WHERE difficulty=2 AND status='ready' ORDER BY question_id LIMIT 10").mappings()]
        q_hard = [r["question_id"] for r in conn.exec_driver_sql("SELECT question_id FROM live.questions WHERE difficulty=3 AND status='ready' ORDER BY question_id LIMIT 5").mappings()]
        for pos, qid in enumerate(q_easy + q_med + q_hard, start=1):
            ex(
                conn,
                """INSERT INTO live.weekly_set_items (set_id, question_id, position, is_voided)
                   VALUES (:s, :q, :p, false) ON CONFLICT DO NOTHING""",
                s=set_id,
                q=qid,
                p=pos,
            )

    # Khởi tạo lịch sử job & bản nháp bằng cách chạy SQL thật trên enterprise_db (không gán số dòng giả)
    if q1(conn, "SELECT count(*) AS n FROM draft.generation_jobs")["n"] == 0:
        job = q1(
            conn,
            """INSERT INTO draft.generation_jobs
               (world_id, triggered_by, difficulty, skill_ids, topic, requested_count, created_count, failed_count, status, started_at, finished_at)
               VALUES (:w, :u, 2, ARRAY[2,3,5], 'Phân tích đơn hàng, chi phí hoàn tiền & nhân sự trên enterprise_db', 3, 3, 0, 'done', now() - interval '15 minutes', now() - interval '12 minutes')
               RETURNING job_id""",
            w=world_pk,
            u=user_ids[admin_uname],
        )
        jid = job["job_id"]
        seed_draft_specs = [
            (
                "Top 5 phương thức thanh toán có tổng tiền hoàn trả cao nhất",
                "Viết truy vấn thống kê tối đa 5 phương thức thanh toán (payments.payment_method) có tổng giá trị hoàn tiền (refunds.refund_amount) cao nhất. Trả về payment_method, refund_count, total_refund_amount, sắp xếp giảm dần theo total_refund_amount và tăng dần theo payment_method.",
                "SELECT pay.payment_method, COUNT(rf.refund_id)::int AS refund_count, SUM(rf.refund_amount) AS total_refund_amount FROM payments pay JOIN refunds rf ON rf.payment_id = pay.payment_id GROUP BY pay.payment_method ORDER BY total_refund_amount DESC, pay.payment_method ASC LIMIT 5",
                2,
                [2, 3],
                ["payments", "refunds"],
                "needs_human",
                "CONSENSUS_REVIEW: Cần Giảng viên xác nhận có lọc theo trạng thái refund_status = 'completed' hay tính toàn bộ yêu cầu hoàn tiền.",
            ),
            (
                "Nhân viên có doanh số đơn giao thành công vượt mức trung bình phòng ban",
                "Liệt kê các nhân viên có tổng giá trị đơn hàng đã giao thành công (orders.status = 'delivered') lớn hơn mức trung bình của các nhân viên trong cùng phòng ban. Trả về employee_id, full_name, department_id, total_sales, sắp xếp giảm dần theo total_sales và tăng dần theo employee_id.",
                "WITH emp_sales AS (SELECT e.employee_id, e.full_name, e.department_id, COALESCE(SUM(o.total_amount), 0) AS total_sales FROM employees e LEFT JOIN orders o ON o.employee_id = e.employee_id AND o.status = 'delivered' GROUP BY e.employee_id, e.full_name, e.department_id), dept_avg AS (SELECT department_id, AVG(total_sales) AS avg_sales FROM emp_sales GROUP BY department_id) SELECT s.employee_id, s.full_name, s.department_id, s.total_sales FROM emp_sales s JOIN dept_avg d ON d.department_id = s.department_id WHERE s.total_sales > d.avg_sales ORDER BY s.total_sales DESC, s.employee_id ASC",
                3,
                [4, 5],
                ["employees", "orders"],
                "needs_human",
                "SEMANTIC_REVIEW: Cần Giảng viên xác nhận nhân viên chưa xử lý đơn nào có tính vào mẫu số trung bình phòng ban không.",
            ),
            (
                "Khách hàng có từ 3 đơn hàng đã giao thành công trở lên",
                "Tìm các khách hàng có ít nhất 3 đơn hàng ở trạng thái 'delivered'. Trả về customer_id, full_name, delivered_order_count, total_spent, sắp xếp giảm dần theo total_spent và tăng dần theo customer_id.",
                "SELECT c.customer_id, c.full_name, COUNT(o.order_id)::int AS delivered_order_count, SUM(o.total_amount) AS total_spent FROM customers c JOIN orders o ON o.customer_id = c.customer_id WHERE o.status = 'delivered' GROUP BY c.customer_id, c.full_name HAVING COUNT(o.order_id) >= 3 ORDER BY total_spent DESC, c.customer_id ASC",
                1,
                [2, 3],
                ["customers", "orders"],
                "approved",
                "PASS_CALIBRATED_GATES: Khớp kết quả thực thi trên PostgreSQL 17 enterprise_db.",
            ),
        ]
        for title, qtxt, rsql, diff, sks, tbls, st, reason in seed_draft_specs:
            exec_real = submissions.execute_sandbox_sql(rsql)
            out_cols = list(exec_real.get("columns", []))
            real_rows = [[submissions.json_value(row.get(c)) for c in out_cols] for row in exec_real.get("rows", [])]
            real_rc = int(exec_real.get("row_count", len(real_rows)))
            rhash = hashlib.sha256(_j(real_rows).encode("utf-8")).hexdigest()
            bp = {
                "candidate": {
                    "business_domain": "sales_analytics",
                    "business_goal": title,
                    "difficulty_reason": reason,
                    "output_columns": out_cols,
                },
                "source_question_ids": [1, 2],
            }
            vr = {"passed": st == "approved", "row_count": real_rc, "columns": out_cols, "reason": reason}
            drow = q1(
                conn,
                """INSERT INTO draft.question_drafts
                   (world_id, job_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, blueprint, tables_used, schema_text, validation_report, status, status_reason, gen_model, gen_prompt_version, review_attempts)
                   VALUES (:w, :j, :t, :q, :sql, 'ordered', :d, :sk, CAST(:bp AS jsonb), :tu, :stxt, CAST(:vr AS jsonb), :st, :r, 'Model A', 'v2.4-ct', 1)
                   RETURNING *""",
                w=world_pk,
                j=jid,
                t=title,
                q=qtxt,
                sql=rsql,
                d=diff,
                sk=sks,
                bp=_j(bp),
                tu=tbls,
                stxt=f"-- Bảng sử dụng: {', '.join(tbls)}",
                vr=_j(vr),
                st=st,
                r=reason,
            )
            did = drow["draft_id"]
            ex(
                conn,
                """INSERT INTO draft.self_solve_runs (draft_id, sample_index, model_sql, is_selected, matched_datasets, total_datasets, exec_status, row_count, review_model, review_round)
                   VALUES (:d, 0, :sql, true, 1, 1, 'ok', :rc, 'Model B', 1)""",
                d=did,
                sql=rsql,
                rc=real_rc,
            )
            ex(
                conn,
                """INSERT INTO draft.review_logs (draft_id, stage, passed, score, reasons, review_model, rubric_version)
                   VALUES (:d, 'decision', :p, :sc, CAST(:rs AS jsonb), 'Model B', 'rubric-v7')""",
                d=did,
                p=(st == "approved"),
                sc=(96.0 if st == "approved" else 80.0),
                rs=_j([reason]),
            )
            if st == "approved" and real_rc > 0:
                promotion.promote(
                    conn,
                    dict(drow),
                    1,
                    "ordered",
                    rsql,
                    [
                        {
                            "dataset_ref": "enterprise/base",
                            "dataset_version": 1,
                            "compare_mode": "ordered",
                            "expected_columns": out_cols,
                            "expected_rows": real_rows,
                            "row_count": real_rc,
                            "result_hash": rhash,
                        }
                    ],
                )

    # Khởi tạo lịch sử nộp bài bằng cách chấm thực thi thật trên enterprise_db (đo runtime_ms thực tế)
    if q1(conn, "SELECT count(*) AS n FROM live.submissions")["n"] == 0:
        pub_set = q1(conn, "SELECT set_id FROM live.weekly_sets WHERE status='published'")
        sid = pub_set["set_id"] if pub_set else None
        if sid:
            qs = q(
                conn,
                """SELECT q.question_id, q.reference_sql
                   FROM live.weekly_set_items wsi
                   JOIN live.questions q USING (question_id)
                   WHERE wsi.set_id = :s
                   ORDER BY wsi.position
                   LIMIT 8""",
                s=sid,
            )
            learner_progress_plan = [
                (user_ids["tuan_b22"], 7),
                (user_ids["nguyen_b22"], 5),
                (user_ids["ha_b22"], 4),
                (user_ids[learner_uname], 2),
            ]
            for uid, solved_n in learner_progress_plan:
                for qrow in qs[:solved_n]:
                    exec_sub = submissions.execute_sandbox_sql(qrow["reference_sql"])
                    measured_ms = max(1, int(round(float(exec_sub.get("runtime_ms") or 3))))
                    ex(
                        conn,
                        """INSERT INTO live.submissions (user_id, question_id, set_id, submitted_sql, submission_status, execution_status, score, runtime_ms)
                           VALUES (:u, :q, :s, :sql, 'passed', 'passed', 100.0, :ms)""",
                        u=uid,
                        q=qrow["question_id"],
                        s=sid,
                        sql=qrow["reference_sql"],
                        ms=measured_ms,
                    )
            ex(
                conn,
                """UPDATE live.questions q
                   SET pass_rate = sub_stats.rate
                   FROM (
                     SELECT question_id,
                            ROUND(100.0 * SUM(CASE WHEN submission_status = 'passed' THEN 1 ELSE 0 END) / GREATEST(COUNT(*), 1), 1) AS rate
                     FROM live.submissions
                     GROUP BY question_id
                   ) sub_stats
                   WHERE q.question_id = sub_stats.question_id""",
            )

    # Khởi tạo nhóm đề nháp từ các câu hỏi ready chưa gán vào bộ đề tuần
    sample_group_name = "Nhóm đề Thực hành JOIN & Doanh thu (Chờ đăng)"
    if not q1(conn, "SELECT group_id FROM live.question_groups WHERE name=:n", n=sample_group_name):
        unassigned_qids = [
            r["question_id"]
            for r in conn.exec_driver_sql(
                """SELECT q.question_id
                   FROM live.questions q
                   WHERE q.status = 'ready'
                     AND NOT EXISTS (SELECT 1 FROM live.weekly_set_items wsi WHERE wsi.question_id = q.question_id)
                   ORDER BY q.question_id ASC
                   LIMIT 4"""
            ).mappings()
        ]
        if unassigned_qids:
            grp_row = q1(
                conn,
                """INSERT INTO live.question_groups (name, description, status, created_by)
                   VALUES (:n, :d, 'draft', :u) RETURNING group_id""",
                n=sample_group_name,
                d="Nhóm câu hỏi thực hành truy vấn nối bảng (JOIN) và thống kê doanh thu chờ Giảng viên phát hành hàng loạt.",
                u=user_ids[admin_uname],
            )
            gid = grp_row["group_id"]
            for pos, qid in enumerate(unassigned_qids, start=1):
                ex(
                    conn,
                    "INSERT INTO live.question_group_items (group_id, question_id, position) VALUES (:g, :q, :p) ON CONFLICT DO NOTHING",
                    g=gid,
                    q=qid,
                    p=pos,
                )

    return {"users": len(user_ids), "questions": q1(conn, "SELECT count(*) AS n FROM live.questions")["n"]}
