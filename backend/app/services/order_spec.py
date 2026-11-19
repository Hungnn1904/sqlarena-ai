"""Đồng bộ mệnh đề ORDER BY cấp ngoài cùng (top-level) của reference_sql với nội dung đề bài tiếng Việt và compare_mode."""
from __future__ import annotations

import re

_DOLLAR_TAG_RE = re.compile(r"^\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def _mask_non_code_tokens(sql: str, *, keep_literals_and_idents: bool = False) -> str:
    """Ẩn comment (-- và /* */), chuỗi '...' / $$...$$ và định danh "..." để dò từ khóa/dấu phẩy cấp 0 chính xác."""
    out = list(sql)
    n = len(out)
    i = 0
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        # 1. Single-quoted string literal '...'
        if ch == "'":
            if not keep_literals_and_idents:
                out[i] = " "
            i += 1
            while i < n:
                if sql[i] == "'" and i + 1 < n and sql[i + 1] == "'":
                    if not keep_literals_and_idents:
                        out[i] = " "
                        out[i + 1] = " "
                    i += 2
                    continue
                if sql[i] == "'":
                    if not keep_literals_and_idents:
                        out[i] = " "
                    i += 1
                    break
                if not keep_literals_and_idents:
                    out[i] = " "
                i += 1
            continue

        # 2. Double-quoted identifier "..."
        if ch == '"':
            if not keep_literals_and_idents:
                out[i] = " "
            i += 1
            while i < n:
                if sql[i] == '"' and i + 1 < n and sql[i + 1] == '"':
                    if not keep_literals_and_idents:
                        out[i] = " "
                        out[i + 1] = " "
                    i += 2
                    continue
                if sql[i] == '"':
                    if not keep_literals_and_idents:
                        out[i] = " "
                    i += 1
                    break
                if not keep_literals_and_idents:
                    out[i] = " "
                i += 1
            continue

        # 3. PostgreSQL dollar-quoted literal $$...$$ or $tag$...$tag$
        if ch == "$":
            m_tag = _DOLLAR_TAG_RE.match(sql[i:])
            if m_tag:
                tag = m_tag.group(0)
                end_idx = sql.find(tag, i + len(tag))
                stop = (end_idx + len(tag)) if end_idx != -1 else n
                if not keep_literals_and_idents:
                    for k in range(i, stop):
                        out[k] = " "
                i = stop
                continue

        # 4. Line comment --...\n
        if ch == "-" and nxt == "-":
            while i < n and sql[i] != "\n":
                out[i] = " "
                i += 1
            continue

        # 5. Block comment /*...*/
        if ch == "/" and nxt == "*":
            out[i] = " "
            out[i + 1] = " "
            i += 2
            while i < n:
                if sql[i] == "*" and i + 1 < n and sql[i + 1] == "/":
                    out[i] = " "
                    out[i + 1] = " "
                    i += 2
                    break
                out[i] = " "
                i += 1
            continue

        i += 1
    return "".join(out)


def _strip_comments_preserve_code(sql: str) -> str:
    return _mask_non_code_tokens(sql, keep_literals_and_idents=True)


def _strip_comments_and_strings(sql: str) -> str:
    return _mask_non_code_tokens(sql, keep_literals_and_idents=False)


def _split_top_level_commas(segment: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    masked = _strip_comments_and_strings(segment)
    for idx, ch in enumerate(masked):
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(segment[start:idx].strip())
            start = idx + 1
    tail = segment[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def extract_top_level_order_by(sql: str | None, output_columns: list[str] | None = None) -> list[tuple[str, str]]:
    """Trả về danh sách [(biểu_thức_cột, 'ASC'|'DESC')] của mệnh đề ORDER BY cấp 0 ngoài cùng; [] nếu không có."""
    if not sql or not sql.strip():
        return []
    no_comments = _strip_comments_preserve_code(sql).strip().rstrip(";").strip()
    if not no_comments:
        return []
    masked = _strip_comments_and_strings(no_comments)

    depths = [0] * len(masked)
    d = 0
    for idx, ch in enumerate(masked):
        if ch == "(":
            d += 1
        depths[idx] = d
        if ch == ")" and d > 0:
            d -= 1

    # Nếu có phép hợp/giao/trừ tập hợp cấp 0 (UNION / INTERSECT / EXCEPT), chỉ xét ORDER BY sau toán tử tập hợp cuối cùng
    min_pos = 0
    for set_op in re.finditer(r"\b(?:UNION|INTERSECT|EXCEPT)\b", masked, flags=re.IGNORECASE):
        if depths[set_op.start()] == 0:
            min_pos = set_op.end()

    last_match = None
    for m in re.finditer(r"\bORDER\s+BY\b", masked, flags=re.IGNORECASE):
        if m.start() >= min_pos and depths[m.start()] == 0:
            last_match = m
    if not last_match:
        return []

    clause_start = last_match.end()
    clause_end = len(no_comments)
    tail_masked = masked[clause_start:]
    for kw in re.finditer(r"\b(?:LIMIT|OFFSET|FETCH|FOR)\b", tail_masked, flags=re.IGNORECASE):
        abs_pos = clause_start + kw.start()
        if depths[abs_pos] == 0:
            clause_end = abs_pos
            break

    clause = no_comments[clause_start:clause_end].strip()
    if not clause:
        return []

    specs: list[tuple[str, str]] = []
    out_cols = list(output_columns or [])
    for item in _split_top_level_commas(clause):
        cleaned = re.sub(r"\s+NULLS\s+(?:FIRST|LAST)\s*$", "", item.strip(), flags=re.IGNORECASE).strip()
        m_dir = re.match(r"^(.*?)\s+(ASC|DESC)\s*$", cleaned, flags=re.IGNORECASE | re.DOTALL)
        if m_dir:
            expr = m_dir.group(1).strip()
            direction = m_dir.group(2).upper()
        else:
            expr = cleaned
            direction = "ASC"

        if expr.isdigit():
            pos = int(expr)
            if 1 <= pos <= len(out_cols):
                expr = str(out_cols[pos - 1])
        elif len(expr) >= 2 and expr.startswith('"') and expr.endswith('"'):
            expr = expr[1:-1].replace('""', '"')
        else:
            m_alias = re.match(r"^[A-Za-z_][A-Za-z0-9_]*\.([A-Za-z_][A-Za-z0-9_]*)$", expr)
            if m_alias:
                expr = m_alias.group(1)
        expr = re.sub(r"\s+", " ", expr).strip()
        if expr:
            specs.append((expr, direction))
    return specs


def format_order_requirement_vi(specs: list[tuple[str, str]]) -> str:
    parts = [
        f"{col} {'giảm dần (DESC)' if direction == 'DESC' else 'tăng dần (ASC)'}"
        for col, direction in specs
    ]
    return f"Yêu cầu sắp xếp: Sắp xếp kết quả theo {', '.join(parts)}."


def sync_question_order_contract(
    question_text: str,
    reference_sql: str | None,
    compare_mode: str | None = None,
    output_columns: list[str] | None = None,
) -> tuple[str, str]:
    """Đồng bộ compare_mode và bổ sung câu Yêu cầu sắp xếp rõ ràng vào đề bài nếu reference_sql có ORDER BY."""
    q_clean = (question_text or "").strip()
    if not reference_sql or not reference_sql.strip():
        return q_clean, (compare_mode or "unordered")

    specs = extract_top_level_order_by(reference_sql, output_columns)
    if not specs:
        return q_clean, "unordered"

    if not re.search(r"sắp\s+xếp", q_clean, flags=re.IGNORECASE):
        req_line = format_order_requirement_vi(specs)
        q_clean = f"{q_clean}\n\n{req_line}" if q_clean else req_line
    return q_clean, "ordered"
