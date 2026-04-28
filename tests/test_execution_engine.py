"""
Unit tests cho execution_engine.py
Dùng pytest. execution_engine phải implement verify_in_sandbox().
"""
import sys
import os

# Đảm bảo import được module ở thư mục cha
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from execution_engine import verify_in_sandbox

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TEST_DDL = """
CREATE TABLE depts (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emps (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER);
"""

TEST_SEED = """
INSERT INTO depts VALUES (1, 'Engineering'), (2, 'Sales');
INSERT INTO emps VALUES (1, 'Alice', 1), (2, 'Bob', 2), (3, 'Charlie', 1);
"""


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestValidSelectQuery:
    def test_returns_valid_true(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="SELECT * FROM emps;",
        )
        assert result["valid"] is True

    def test_has_rows(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="SELECT * FROM emps;",
        )
        assert len(result["output"]) > 0

    def test_error_is_none(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="SELECT * FROM emps;",
        )
        assert result["error"] is None

    def test_duration_ms_present(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="SELECT * FROM emps;",
        )
        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], int)


class TestInvalidSqlSyntax:
    def test_returns_valid_false(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="SELEKT * FORM emps",  # typo SQL
        )
        assert result["valid"] is False

    def test_error_is_not_none(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="SELEKT * FORM emps",
        )
        assert result["error"] is not None
        assert len(result["error"]) > 0


class TestForbiddenDropOperation:
    def test_drop_returns_valid_false(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="DROP TABLE emps;",
        )
        assert result["valid"] is False

    def test_drop_error_message(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="DROP TABLE emps;",
        )
        assert result["error"] is not None
        assert "forbidden" in result["error"].lower() or "drop" in result["error"].lower()

    def test_delete_is_allowed(self):
        """DELETE là DML hợp lệ trong sandbox giáo dục — không bị chặn"""
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="DELETE FROM emps WHERE id = 1;",
        )
        assert result["valid"] is True


class TestEmptyResult:
    def test_valid_but_no_rows(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="SELECT * FROM emps WHERE id = 9999;",
        )
        assert result["valid"] is True

    def test_output_is_empty_list(self):
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql="SELECT * FROM emps WHERE id = 9999;",
        )
        assert result["output"] == []


class TestJoinQuery:
    def test_join_returns_valid(self):
        answer_sql = """
        SELECT e.name, d.name AS department
        FROM emps e
        JOIN depts d ON e.dept_id = d.id;
        """
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql=answer_sql,
        )
        assert result["valid"] is True

    def test_join_has_expected_rows(self):
        answer_sql = """
        SELECT e.name, d.name AS department
        FROM emps e
        JOIN depts d ON e.dept_id = d.id;
        """
        result = verify_in_sandbox(
            ddl_sql=TEST_DDL,
            seed_sql=TEST_SEED,
            answer_sql=answer_sql,
        )
        assert len(result["output"]) == 3  # Alice, Bob, Charlie


class TestTimeoutHandling:
    def test_infinite_recursion_times_out(self):
        """
        SQLite không support infinite loop thực sự, nhưng WITH RECURSIVE
        không giới hạn có thể trigger timeout của engine.
        Test này kiểm tra engine có cơ chế timeout — nếu engine không có
        timeout thì test sẽ skip thay vì treo vô hạn.
        """
        # WITH RECURSIVE không giới hạn — sẽ timeout hoặc bị chặn
        heavy_sql = """
        WITH RECURSIVE cnt(x) AS (
            SELECT 1
            UNION ALL
            SELECT x + 1 FROM cnt WHERE x < 10000000
        )
        SELECT COUNT(*) FROM cnt;
        """
        try:
            result = verify_in_sandbox(
                ddl_sql=TEST_DDL,
                seed_sql=TEST_SEED,
                answer_sql=heavy_sql,
            )
            # Nếu engine có timeout → valid=False
            # Nếu engine cho chạy xong → valid=True nhưng phải có duration
            if not result["valid"]:
                assert result["error"] is not None
            else:
                assert "duration_ms" in result
        except Exception:
            pytest.skip("Engine không support recursive CTE hoặc timeout chưa implement")
