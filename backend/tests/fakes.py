"""FakeOllama: transport giả cho test — thay *chỉ* HTTP tới Ollama; toàn bộ engine (validator, guard, thực thi SQL thật
trên Enterprise DB, consensus, test-case) vẫn chạy thật. Dùng để kiểm thử điều phối, KHÔNG chứng minh chất lượng model thật."""
import json

TOPIC = "Human Resources"
MODEL_A_GOOD = {
    "title": "Nhân viên đang làm việc vào công ty từ năm 2024",
    "question": ("Liệt kê nhân viên có status='active' và hire_date >= 2024-01-01. "
                 "Cột kết quả theo thứ tự: employee_id, full_name, job_title, hire_date. "
                 "Sắp xếp: hire_date giảm dần, employee_id tăng. "
                 "Quy tắc biên: Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu."),
    "business_domain": "Human Resources",
    "business_goal": "Theo dõi nhân sự mới gia nhập gần đây",
    "difficulty_reason": "Chỉ lọc và sắp xếp trên một bảng.",
    "difficulty": "easy", "primary_skill_group": "S1", "skills": ["S1"],
    "tables_used": ["employees"], "output_columns": ["employee_id", "full_name", "job_title", "hire_date"],
    "required_columns": {"employees": ["employee_id", "full_name", "job_title", "hire_date", "status"]},
    "table_roles": {"employees": "Bảng nhân viên cần lọc"},
    "logic_signature": {"output_grain": "Một nhân viên", "analysis_goal": "Lọc nhân sự mới đang làm việc",
                        "filter_pattern": "status active và hire_date từ mốc 2024", "aggregation_pattern": "Không tổng hợp"},
    "join_relations": [],
}
GOOD_SQL = "SELECT employee_id, full_name, job_title, hire_date FROM employees WHERE status = 'active' AND hire_date >= DATE '2024-01-01' ORDER BY hire_date DESC, employee_id"
GOOD_SQL_ALT = "SELECT e.employee_id, e.full_name, e.job_title, e.hire_date FROM employees e WHERE e.hire_date >= DATE '2024-01-01' AND e.status = 'active' ORDER BY e.hire_date DESC, e.employee_id ASC"
WRONG_SQL = "SELECT employee_id, full_name, job_title, hire_date FROM employees WHERE status = 'active' AND hire_date >= DATE '2024-06-01' ORDER BY hire_date DESC, employee_id"
AUDIT_PASS = {"verdict": "pass", "issues": [], "checks": [
    {"requirement": r, "status": "pass", "finding": "Khớp yêu cầu của đề."} for r in
    ("output columns and aliases", "WHERE, HAVING, aggregate thresholds", "joins, row grain, EXISTS and correlated subqueries",
     "NULL, date, rounding, unit edge cases", "ordering and tie breakers")]}


class FakeOllama:
    """Kịch bản theo vai trò: Model A / Model B(solver) / auditor. Đếm số call để test ledger/budget."""

    def __init__(self, model_a=None, solver_sqls=None, audit=None, fail_with: Exception | None = None):
        self.model_a = [model_a if model_a is not None else MODEL_A_GOOD]
        self.solver_sqls = list(solver_sqls or [GOOD_SQL, GOOD_SQL_ALT, GOOD_SQL])
        self.audit = audit if audit is not None else AUDIT_PASS
        self.fail_with = fail_with
        self.calls = {"model_a": 0, "solver": 0, "auditor": 0}

    def __call__(self, config, path, body=None):
        if path == "/api/tags":
            return {"models": [{"name": config["MODEL_NAME"]}]}
        if self.fail_with:
            raise self.fail_with
        props = (body.get("format") or {}).get("properties", {}) if isinstance(body.get("format"), dict) else {}
        meta = {"done": True, "done_reason": "stop", "prompt_eval_count": 100, "eval_count": 50, "total_duration": 1}
        if "title" in props:
            self.calls["model_a"] += 1
            item = self.model_a[min(self.calls["model_a"] - 1, len(self.model_a) - 1)]
            return {**meta, "response": json.dumps(item)}
        if "verdict" in props:
            self.calls["auditor"] += 1
            return {**meta, "response": json.dumps(self.audit)}
        self.calls["solver"] += 1
        sql = self.solver_sqls[(self.calls["solver"] - 1) % len(self.solver_sqls)]
        return {**meta, "response": json.dumps({"sql": sql})}
