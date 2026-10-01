import io
import json
import re
import time
import warnings
from bs4 import BeautifulSoup
import easyocr
import numpy as np
import pandas as pd
from PIL import Image
import requests
from curl_cffi import requests as cffi_requests

# Tắt cảnh báo không cần thiết từ PyTorch / EasyOCR
warnings.filterwarnings('ignore', category=UserWarning)

# =========================================================================
# 1. BỘ TỪ ĐIỂN VÀ HÀM LÀM SẠCH / PHÂN LOẠI CHUẨN HÓA
# =========================================================================

VALID_SQL_TYPES = {
    'integer', 'int', 'varchar', 'text', 'datetime', 'timestamp', 
    'decimal', 'float', 'numeric', 'boolean', 'bigint', 'smallint', 
    'date', 'string', 'char', 'time', 'json', 'enum', 'number', 'varchar2'
}

def clean_text_single_line(text):
    """Làm sạch ký tự HTML, Markdown, trả về text trên 1 dòng duy nhất."""
    if not text:
        return ""
    text = re.sub(r'<style[\s\S]*?</style>', '', str(text), flags=re.IGNORECASE)
    text = re.sub(r'<script[\s\S]*?</script>', '', str(text), flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'[`\*_]', '', text)
    text = re.sub(r'\|.*?\|', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def infer_business_context(title, content, company=""):
    """Tự động gán bối cảnh doanh nghiệp theo từ khóa."""
    text = (str(title) + " " + str(content) + " " + str(company)).lower()
    if any(k in text for k in ['contest', 'hacker', 'leaderboard', 'competition', 'student', 'grade', 'marks', 'school', 'university', 'academic']):
        return "Giáo dục & Thi đấu lập trình"
    if any(k in text for k in ['restaurant', 'food', 'yelp', 'doordash', 'dining', 'meal', 'beverage', 'drink', 'pizza']):
        return "Nhà hàng & Dịch vụ Ẩm thực"
    if any(k in text for k in ['ride', 'uber', 'airbnb', 'trip', 'bike', 'driver', 'hotel', 'flight', 'station', 'bus', 'weather']):
        return "Dịch vụ Vận tải & Du lịch"
    if any(k in text for k in ['order', 'product', 'customer', 'purchase', 'amazon', 'store', 'sale', 'retail', 'inventory', 'item', 'price', 'market']):
        return "Thương mại điện tử & Bán lẻ"
    if any(k in text for k in ['user', 'tweet', 'post', 'facebook', 'twitter', 'meta', 'friend', 'like', 'reaction', 'page', 'session', 'snap', 'activity']):
        return "Mạng xã hội & Truyền thông số"
    if any(k in text for k in ['salary', 'employee', 'department', 'worker', 'hire', 'manager', 'bonus', 'payroll', 'title', 'occupation']):
        return "Quản trị Nhân sự & Tiền lương"
    if any(k in text for k in ['bank', 'account', 'transaction', 'credit', 'loan', 'tax', 'payment', 'revenue', 'profit', 'investment']):
        return "Tài chính & Ngân hàng"
    if any(k in text for k in ['patient', 'hospital', 'doctor', 'drug', 'pharmacy', 'medical', 'health']):
        return "Y tế & Dược phẩm"
    return "Doanh nghiệp / Phân tích dữ liệu sản phẩm"

def classify_sql_technique(title, content):
    """Tự động phân loại kỹ thuật SQL."""
    text = (str(title) + " " + str(content)).lower()
    if re.search(r'\bdense_rank\b|\brank\b|\bconsecutive\b|\bnth highest\b|\btop \d+\b|\brow_number\b|\blag\b|\blead\b|\brolling\b', text):
        return "Window Functions & Ranking"
    if re.search(r'\baverage\b|\bavg\b|\bsum\b|\btotal\b|\bcount\b|\bmaximum\b|\bminimum\b|\bgroup by\b|\bfor each\b|\bhaving\b|\bpercentage\b', text):
        return "Aggregation & Grouping"
    if re.search(r'\bjoin\b|\bmatching pairs\b|\bboth tables\b|\bnever sold\b|\bnot exist\b|\bcombine\b|\btwo tables\b', text):
        return "Joins & Subqueries"
    if re.search(r'\bcase when\b|\bifnull\b|\bcoalesce\b|\bdifference\b|\bproportion\b|\bswap\b|\bdate', text):
        return "Conditional Logic & Functions"
    return "Basic Select & Filtering"

def extract_keywords_exact(title, content):
    """Trích xuất từ khóa SQL chính xác bằng Regex ranh giới từ."""
    text = (str(title) + " " + str(content)).lower()
    found = []
    rules = {
        'COUNT()': r'\bcount\b|\bnumber of\b|\bhow many\b',
        'SUM()': r'\bsum\b|\btotal amount\b|\btotal sales\b|\btotal revenue\b|\btotal earnings\b',
        'AVG()': r'\baverage\b|\bavg\b|\bmean\b',
        'GROUP BY': r'\bgroup by\b|\bgrouped by\b|\bfor each\b|\bper each\b',
        'HAVING': r'\bhaving\b|\bat least \d+\b|\bfewer than \d+\b|\bmore than \d+\b',
        'LEFT JOIN': r'\bleft join\b|\bnever\b|\bnot exist\b|\bwithout\b',
        'INNER JOIN': r'\bmatching pairs\b|\bboth tables\b|\binner join\b|\bjoined\b|\bmatch\b',
        'ORDER BY': r'\border by\b|\bdescending\b|\bascending\b|\bsorted\b',
        'DENSE_RANK()': r'\bdense_rank\b|\btop \d+\b|\bnth highest\b|\brank\b|\branking\b',
        'ROW_NUMBER()': r'\brow_number\b|\bconsecutive\b',
        'CASE WHEN': r'\bcase when\b|\bifnull\b|\bcoalesce\b|\bconditional\b|\bproportion\b',
        'DISTINCT': r'\bdistinct\b|\bunique\b'
    }
    for label, pattern in rules.items():
        if re.search(pattern, text):
            found.append(label)
    return ", ".join(found[:4]) if found else "SELECT, WHERE"

# =========================================================================
# 2. XỬ LÝ SCHEMA LEETCODE & HACKERRANK (OCR TỌA ĐỘ DÒNG)
# =========================================================================

def extract_leetcode_schema_exact(raw_html):
    if not raw_html:
        return "Schema mô tả trong đề"

    soup = BeautifulSoup(raw_html, 'html.parser')
    for tag in soup.find_all(['p', 'div', 'strong', 'pre']):
        text_lower = tag.get_text().lower()
        if any(k in text_lower for k in ['example 1:', 'example 2:', 'explanation:']):
            for sibling in list(tag.find_next_siblings()):
                sibling.decompose()
            tag.decompose()
            break

    schemas = []
    tables = soup.find_all('table')
    for tbl in tables:
        tb_name = "table_data"
        prev_tag = tbl.find_previous(['p', 'h3', 'h4', 'strong', 'b'])
        if prev_tag:
            m = re.search(r'Table:\s*`?([a-zA-Z0-9_]+)`?', prev_tag.get_text(), re.I)
            if not m:
                code_tag = prev_tag.find('code')
                if code_tag:
                    tb_name = code_tag.get_text(strip=True)
            else:
                tb_name = m.group(1).strip()
        
        cols = []
        for tr in tbl.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th']) if td]
            if len(cells) >= 2:
                c_name = cells[0].strip()
                c_type = cells[1].strip().lower()
                if c_type in VALID_SQL_TYPES and c_name.lower() not in ['column_name', 'column name', 'field', 'type']:
                    cols.append(f"{c_name} {c_type}")
        if cols:
            schemas.append(f"{tb_name} ({', '.join(cols)})")

    if not schemas:
        pre_tags = soup.find_all('pre')
        for pre in pre_tags:
            txt = pre.get_text()
            if '|' in txt and ('column_name' in txt.lower() or 'type' in txt.lower()):
                prev_tag = pre.find_previous(['p', 'strong', 'b'])
                tb_name = "table_data"
                if prev_tag:
                    m = re.search(r'Table:\s*`?([a-zA-Z0-9_]+)`?', prev_tag.get_text(), re.I)
                    if m:
                        tb_name = m.group(1).strip()
                rows = re.findall(r'\|\s*([a-zA-Z0-9_]+)\s*\|\s*([a-zA-Z0-9_]+)\s*\|', txt)
                cols = [
                    f"{c} {t.lower()}" 
                    for c, t in rows 
                    if t.lower() in VALID_SQL_TYPES and c.lower() not in ['column_name', 'type']
                ]
                if cols:
                    schemas.append(f"{tb_name} ({', '.join(cols)})")

    return " | ".join(schemas) if schemas else "Schema mô tả trong đề"

def preprocess_image_for_ocr(img_bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            alpha = img.convert('RGBA').split()[-1]
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            bg.paste(img, mask=alpha)
            img = bg.convert('RGB')
        else:
            img = img.convert('RGB')
            
        w, h = img.size
        img = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        return np.array(img)
    except Exception:
        return None

def normalize_sql_column_line(line_text):
    """
    Chuẩn hóa 1 dòng OCR chứa: Tên cột + Kiểu dữ liệu.
    Xử lý triệt để VARCHARZ, số trong ngoặc, dấu phẩy/ngoặc rác.
    """
    txt = line_text.strip()
    if re.search(r'\b(Field|Type|Column|Null|Key)\b', txt, re.I):
        return None

    # 1. Sửa lỗi OCR: VARCHARZ / VARCHAR 2 / VARCHAR -> VARCHAR2(N)
    txt = re.sub(r'VARCHAR[Zz2\s]+(?:\(?\s*(\d+)\s*\)?|\s+(\d+))?', r'VARCHAR2(\1\2)', txt, flags=re.I)
    txt = re.sub(r'VARCHAR2\(None\)|VARCHAR2\(\)', r'VARCHAR2', txt)

    # 2. Sửa lỗi NUMBER / INTEGER
    txt = re.sub(r'NUMBER(?:\(\s*\d+\s*\))?', 'NUMBER', txt, flags=re.I)
    txt = re.sub(r'INTEGER', 'INTEGER', txt, flags=re.I)

    # 3. Dọn sạch dấu ngoặc, dấu phẩy thừa ở giữa
    txt = txt.replace(',', ' ').replace('`', '').replace("'", "")
    txt = re.sub(r'\s+', ' ', txt).strip()

    # 4. Bắt cặp: [TÊN_CỘT] [KIỂU_DỮ_LIỆU]
    match = re.search(r'([A-Z0-9_]+)\s+(VARCHAR2(?:\(\d+\))?|NUMBER|INTEGER|DATE|CHAR(?:\(\d+\))?|STRING|FLOAT|INT)', txt, re.I)
    if match:
        return f"{match.group(1).upper()} {match.group(2).upper()}"
    return None

def extract_hackerrank_schema(raw_html, soup, ocr_reader, session):
    if not raw_html:
        return "Schema mô tả trong đề"

    schemas = []

    # 1. Quét bảng HTML thuần nếu có
    for tbl in soup.find_all('table'):
        cols = []
        tb_name = "TABLE_DATA"
        prev_tag = tbl.find_previous(['p', 'h3', 'h4', 'strong', 'b'])
        if prev_tag:
            m = re.search(r'([a-zA-Z0-9_]+)\s+(?:table|contains|is described)', prev_tag.get_text(), re.I)
            if m:
                tb_name = m.group(1).strip().upper()

        for tr in tbl.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th']) if td]
            if len(cells) >= 2:
                col_item = normalize_sql_column_line(f"{cells[0]} {cells[1]}")
                if col_item:
                    cols.append(col_item)
        if cols:
            schemas.append(f"{tb_name} ({', '.join(cols)})")

    # 2. Quét qua từng ảnh bằng OCR gom tọa độ dòng Y
    img_tags = soup.find_all('img')
    valid_imgs = [
        img for img in img_tags 
        if 's3.amazonaws.com' in img.get('src', '') and not any(k in img.get('src', '').lower() for k in ['sample', 'output', 'diagram', 'badge'])
    ]

    for img in valid_imgs:
        src = img.get('src', '')
        
        # Bắt tên bảng từ text phía trên ảnh
        tb_name_from_text = ""
        prev_p = img.find_previous(['p', 'h3', 'h4', 'strong', 'b', 'li'])
        if prev_p:
            txt = prev_p.get_text().strip()
            m = re.search(r'^([A-Za-z0-9_]{3,})\s*:', txt)
            if not m:
                m = re.search(r'([A-Za-z0-9_]{3,})\s+(?:table|contains|is described)', txt, re.I)
            if m and m.group(1).upper() not in ['THE', 'TWO', 'FOLLOWING', 'TABLE', 'SAMPLE', 'INPUT', 'OUTPUT']:
                tb_name_from_text = m.group(1).strip().upper()

        try:
            img_res = session.get(src, timeout=8)
            if img_res.status_code == 200:
                img_np = preprocess_image_for_ocr(img_res.content)
                if img_np is not None:
                    ocr_results = ocr_reader.readtext(img_np, detail=1)
                    if not ocr_results:
                        continue

                    # Gom các từ có cùng tọa độ trục Y vào cùng 1 dòng
                    lines_dict = {}
                    for item in ocr_results:
                        bbox, text, _ = item
                        y_center = int((bbox[0][1] + bbox[2][1]) / 2)
                        
                        matched_y = None
                        for y_key in lines_dict.keys():
                            if abs(y_center - y_key) < 18:
                                matched_y = y_key
                                break
                        if matched_y is None:
                            matched_y = y_center
                            lines_dict[matched_y] = []
                        lines_dict[matched_y].append(text.strip())

                    sorted_y = sorted(lines_dict.keys())
                    table_name = tb_name_from_text
                    first_line_text = " ".join(lines_dict[sorted_y[0]])
                    
                    if not table_name:
                        if not re.search(r'\b(Field|Column|Type)\b', first_line_text, re.I):
                            table_name = re.sub(r'[^A-Za-z0-9_]', '', first_line_text).upper()
                        else:
                            url_match = re.search(r'/([a-zA-Z0-9_]+)\.(?:jpg|png|jpeg)', src)
                            table_name = url_match.group(1).upper() if url_match else "TABLE_DATA"

                    # DẠNG 1: Gom các dòng chứa Tên cột & Kiểu dữ liệu
                    cols = []
                    for y in sorted_y:
                        line_str = " ".join(lines_dict[y])
                        col_item = normalize_sql_column_line(line_str)
                        if col_item:
                            cols.append(col_item)

                    # DẠNG 2: Bảng dữ liệu nhiều cột (như Grade | Min_Mark | Max_Mark)
                    if not cols:
                        raw_words = [w.strip() for w in ocr_reader.readtext(img_np, detail=0)]
                        if (len(raw_words) >= 3 and any('grade' in w.lower() for w in raw_words[:3])) or any('mark' in w.lower() for w in raw_words[:3]):
                            table_name = tb_name_from_text or "GRADES"
                            header_cols = [w for w in raw_words[:3] if not w.isdigit() and w.lower() not in ['table', 'the']]
                            if header_cols:
                                cols = [f"{c.upper()} INT" for c in header_cols]

                    if cols:
                        schemas.append(f"{table_name} ({', '.join(cols)})")
        except Exception:
            pass

    # 3. Phân tích ngữ nghĩa văn bản nếu đề bài liệt kê các bảng (như Top Competitors)
    clean_text = soup.get_text()
    if not schemas or any("TABLE_DATA" in s for s in schemas):
        parsed_from_text = []
        pattern = r'([A-Za-z0-9_]{3,}):\s*The\s+([a-zA-Z0-9_]+)\s+is'
        matches = re.findall(pattern, clean_text)
        if matches:
            for tb, primary_col in matches:
                section_match = re.search(rf'{tb}:\s*([^.\n]+(?:\.[^.\n]+)?)', clean_text)
                if section_match:
                    sec_text = section_match.group(1)
                    found_cols = re.findall(r'\b([a-zA-Z0-9_]{2,})\s+is\s+the', sec_text)
                    if found_cols:
                        parsed_from_text.append(f"{tb.upper()} ({', '.join([f'{c.upper()} INT' if 'id' in c.lower() or 'level' in c.lower() or 'score' in c.lower() else f'{c.upper()} VARCHAR' for c in found_cols])})")
            if parsed_from_text:
                return " | ".join(parsed_from_text)

    return " | ".join(schemas) if schemas else "Schema mô tả trong đề"


master_dataset = []

# =========================================================================
# NGUỒN 1: LEETCODE
# =========================================================================
print("=== [1/4] ĐANG CÀO TOÀN BỘ BÀI TẬP LEETCODE ===")
lc_url = "https://leetcode.com/graphql"
lc_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com/problemset/database/"
}

graphql_list_query = {
    "query": """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
        problemsetQuestionList: questionList(
            categorySlug: $categorySlug
            limit: $limit
            skip: $skip
            filters: $filters
        ) {
            total: totalNum
            questions: data {
                frontendQuestionId: questionFrontendId
                title
                titleSlug
                difficulty
                paidOnly: isPaidOnly
            }
        }
    }
    """,
    "variables": {
        "categorySlug": "database",
        "skip": 0,
        "limit": 350,
        "filters": {}
    }
}

detail_query_template = """
query questionContent($titleSlug: String!) {
    question(titleSlug: $titleSlug) {
        content
    }
}
"""

try:
    resp = requests.post(lc_url, json=graphql_list_query, headers=lc_headers)
    data = resp.json().get('data', {}).get('problemsetQuestionList', {})
    questions = data.get('questions', [])
    print(f"=> Tìm thấy tổng cộng {len(questions)} bài từ LeetCode.")

    for item in questions:
        if item.get('paidOnly'):
            continue
            
        q_id = item.get('frontendQuestionId')
        title = item.get('title')
        slug = item.get('titleSlug')
        difficulty = item.get('difficulty')
        
        detail_payload = {
            "query": detail_query_template,
            "variables": {"titleSlug": slug}
        }
        
        det_resp = requests.post(lc_url, json=detail_payload, headers=lc_headers)
        body_text = ""
        schema_info = "Schema mô tả trong đề"
        
        if det_resp.status_code == 200:
            raw_html = det_resp.json().get('data', {}).get('question', {}).get('content', '')
            schema_info = extract_leetcode_schema_exact(raw_html)
            body_text = clean_text_single_line(raw_html)
        
        context = infer_business_context(title, body_text)
        technique = classify_sql_technique(title, body_text)
        keywords = extract_keywords_exact(title, body_text)
        
        master_dataset.append({
            "id": f"LC-SQL-{int(q_id):04d}",
            "nguồn": "LeetCode",
            "đề bài": title,
            "nội dung": body_text if body_text else f"Xem tại: https://leetcode.com/problems/{slug}/",
            "bối cảnh": context,
            "thể loại bài": difficulty,
            "kỹ thuật sử dụng": technique,
            "database_schema": schema_info,
            "từ khoá": keywords
        })
        print(f"-> [LeetCode] #{q_id:<4} {title[:20]:<20} | Schema: {schema_info[:35]}...")
        time.sleep(0.08)
except Exception as e:
    print(f"Lỗi LeetCode: {e}")

# =========================================================================
# NGUỒN 2: STRATASCRATCH - CRAWL THẬT
# =========================================================================
print("\n=== [2/4] ĐANG CÀO DỮ LIỆU TỪ STRATASCRATCH ===")

def detect_sql_features(sql_text):
    """Return detailed SQL features found in a solution or explanation."""
    text = str(sql_text or "").upper()
    if not text.strip():
        return []

    features = []

    def add(feature):
        if feature not in features:
            features.append(feature)

    window_functions = (
        "ROW_NUMBER", "DENSE_RANK", "RANK", "LAG", "LEAD", "NTILE",
        "FIRST_VALUE", "LAST_VALUE",
    )
    for function_name in window_functions:
        if re.search(rf"\b{function_name}\s*\(", text):
            add(function_name)
    if re.search(r"\bOVER\s*\(", text):
        add("OVER")
    if re.search(r"\bPARTITION\s+BY\b", text):
        add("PARTITION BY")

    aggregate_functions = ("COUNT", "SUM", "AVG", "MIN", "MAX")
    for function_name in aggregate_functions:
        if re.search(rf"\b{function_name}\s*\(", text):
            add(function_name)
    if re.search(r"\bGROUP\s+BY\b", text):
        add("GROUP BY")
    if re.search(r"\bHAVING\b", text):
        add("HAVING")

    join_patterns = (
        ("FULL JOIN", r"\bFULL(?:\s+OUTER)?\s+JOIN\b"),
        ("LEFT JOIN", r"\bLEFT(?:\s+OUTER)?\s+JOIN\b"),
        ("RIGHT JOIN", r"\bRIGHT(?:\s+OUTER)?\s+JOIN\b"),
        ("INNER JOIN", r"\bINNER\s+JOIN\b"),
        ("CROSS JOIN", r"\bCROSS\s+JOIN\b"),
    )
    matched_specific_join = False
    for feature, pattern in join_patterns:
        if re.search(pattern, text):
            add(feature)
            matched_specific_join = True
    if not matched_specific_join and re.search(r"\bJOIN\b", text):
        add("JOIN")

    if re.search(r"\bWITH\s+[A-Z_][A-Z0-9_]*\s+AS\s*\(", text):
        add("CTE")
    if re.search(r"\b(?:FROM|IN|EXISTS)\s*\(\s*SELECT\b", text, re.S):
        add("SUBQUERY")

    for feature in ("CASE", "COALESCE", "NULLIF", "CAST"):
        if re.search(rf"\b{feature}\b", text):
            add(feature)

    for feature, pattern in (
        ("UNION ALL", r"\bUNION\s+ALL\b"),
        ("UNION", r"\bUNION\b(?!\s+ALL\b)"),
        ("INTERSECT", r"\bINTERSECT\b"),
        ("EXCEPT", r"\bEXCEPT\b"),
    ):
        if re.search(pattern, text):
            add(feature)

    for feature, pattern in (
        ("DISTINCT", r"\bDISTINCT\b"),
        ("WHERE", r"\bWHERE\b"),
        ("ORDER BY", r"\bORDER\s+BY\b"),
        ("LIMIT", r"\bLIMIT\b"),
        ("DATE_TRUNC", r"\bDATE_TRUNC\s*\("),
        ("DATE_PART", r"\bDATE_PART\s*\("),
        ("EXTRACT", r"\bEXTRACT\s*\("),
        ("STRFTIME", r"\bSTRFTIME\s*\("),
        ("DATE", r"\bDATE\s*\("),
        ("DATETIME", r"\bDATETIME\s*\("),
        ("INTERVAL", r"\bINTERVAL\b"),
    ):
        if re.search(pattern, text):
            add(feature)

    return features


def map_primary_technique(features):
    """Map detailed features to the five existing dataset categories."""
    feature_set = set(features or [])
    window_features = {
        "ROW_NUMBER", "DENSE_RANK", "RANK", "LAG", "LEAD", "NTILE",
        "FIRST_VALUE", "LAST_VALUE", "OVER", "PARTITION BY",
    }
    join_features = {
        "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN",
        "CROSS JOIN", "CTE", "SUBQUERY", "UNION", "UNION ALL",
        "INTERSECT", "EXCEPT",
    }
    aggregate_features = {"COUNT", "SUM", "AVG", "MIN", "MAX", "GROUP BY", "HAVING"}
    conditional_features = {"CASE", "COALESCE", "NULLIF", "CAST"}

    if feature_set & window_features:
        return "Window Functions & Ranking"
    if feature_set & join_features:
        return "Joins & Subqueries"
    if feature_set & aggregate_features:
        return "Aggregation & Grouping"
    if feature_set & conditional_features:
        return "Conditional Logic & Functions"
    return "Basic Select & Filtering"


def features_to_keywords(features):
    return ", ".join(features)

SS_BASE = "https://platform.stratascratch.com"
SS_GRAPHQL_CANDIDATES = [
    "https://api.stratascratch.com/graphql/",
]

# Set STRATASCRATCH_LIMIT=5 for a quick smoke test. Zero crawls all questions.
import os as _ss_os
SS_MAX_QUESTIONS = int(_ss_os.getenv("STRATASCRATCH_LIMIT", "0"))

ss_session = cffi_requests.Session(impersonate="chrome120")

SS_NAV_QUERY = """
query CodingNavigation($codeType: Int!, $q: String, $curatedFilter: Int,
$isFreemium: Boolean, $userSolutionState: String, $companies: [Int],
$industries: [Int], $topics: [Int], $jobPositions: [Int],
$difficulties: [Int], $hasVideoSolution: Boolean, $isBookmarked: Boolean,
$orderField: String) {
  questions: allEducationalQuestions(
    codeType: $codeType
    q: $q
    curatedFilter: $curatedFilter
    isFreemium: $isFreemium
    userSolutionState: $userSolutionState
    companies: $companies
    industries: $industries
    topics: $topics
    jobPositions: $jobPositions
    difficulties: $difficulties
    inDepthSolution: $hasVideoSolution
    isBookmarked: $isBookmarked
    orderField: $orderField
  ) {
    edges {
      node {
        id
        slug
        ... on EducationalQuestionType { title: questionShort }
        isFreemium
      }
    }
  }
}
"""

SS_LAYOUT_QUERY = """
query CodingQuestionLayout($slug: String, $codeType: Int!) {
  educationalQuestion(slug: $slug, codeType: $codeType) {
    id
    url
    questionShort
    difficulty
    debugDifficulty: difficulty(isDebug: true)
    isFreemium
    slug
    tables(codeType: $codeType)
  }
}
"""

SS_SOLUTION_QUERY = """
query Solution($slug: String!, $codeType: Int!, $isDebug: Boolean!) {
  educationalQuestion(slug: $slug) {
    id
    officialOrRecommendedSolution(codeType: $codeType) {
      code
      author
      upvotes
      executionTime
      __typename
    }
    walkthrough(codeType: $codeType, isDebug: $isDebug)
    __typename
  }
}
"""

ss_headers = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": SS_BASE,
    "referer": SS_BASE + "/coding?code_type=1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
}

_ss_graphql_url = None

def ss_graphql(operation_name, query, variables):
    global _ss_graphql_url
    endpoints = [_ss_graphql_url] if _ss_graphql_url else SS_GRAPHQL_CANDIDATES
    errors = []

    for endpoint in endpoints:
        if not endpoint:
            continue
        try:
            res = ss_session.post(
                endpoint,
                json={"operationName": operation_name, "query": query, "variables": variables},
                headers=ss_headers,
                timeout=25,
            )
            preview = (res.text or "")[:160].replace("\n", " ")
            content_type = (res.headers.get("content-type") or "").lower()

            if res.status_code != 200:
                errors.append(f"{endpoint} -> HTTP {res.status_code}: {preview}")
                continue
            if not (res.text or "").strip():
                errors.append(f"{endpoint} -> response rỗng")
                continue
            if "json" not in content_type and not res.text.lstrip().startswith("{"):
                errors.append(f"{endpoint} -> không phải JSON ({content_type}): {preview}")
                continue

            obj = res.json()
            if obj.get("errors"):
                errors.append(f"{endpoint} -> GraphQL errors: {obj['errors']}")
                continue

            _ss_graphql_url = endpoint
            return obj.get("data", {})
        except Exception as e:
            errors.append(f"{endpoint} -> {type(e).__name__}: {e}")

    raise RuntimeError(
        "Không gọi được GraphQL StrataScratch. "
        + " | ".join(errors)
        + " | Nếu vẫn lỗi: DevTools > Network > graphql > Headers > copy Request URL."
    )

def ss_schema_to_text(tables):
    schemas = []
    for table in tables or []:
        table_name = table.get("name") or "table_data"
        columns = []
        for col in table.get("columns") or []:
            col_name = col.get("name")
            col_type = col.get("type")
            if col_name:
                columns.append(f"{col_name} {col_type}".strip() if col_type else col_name)
        if columns:
            schemas.append(f"{table_name} ({', '.join(columns)})")
    return " | ".join(schemas) if schemas else "Schema mô tả trong đề"

def ss_extract_document_metadata(raw_text, expected_slug):
    """Extract the full question from direct JSON or escaped Next.js/RSC data."""
    import html as _html

    metadata = {"question": "", "topics": []}
    if not raw_text or expected_slug not in raw_text:
        return metadata

    variants = [raw_text, _html.unescape(raw_text)]
    for _ in range(2):
        decoded = variants[-1].replace(r'\"', '"').replace(r'\\n', '\n')
        if decoded == variants[-1]:
            break
        variants.append(decoded)

    decoder = json.JSONDecoder()
    for text in variants:
        marker = '"question"'
        position = 0
        while True:
            position = text.find(marker, position)
            if position < 0:
                break
            window = text[max(0, position - 20000):min(len(text), position + 30000)]
            if expected_slug not in window:
                position += len(marker)
                continue
            colon = text.find(":", position + len(marker))
            value_start = colon + 1
            while value_start > 0 and value_start < len(text) and text[value_start].isspace():
                value_start += 1
            try:
                value, _ = decoder.raw_decode(text[value_start:])
                if isinstance(value, str) and len(clean_text_single_line(value)) >= 20:
                    metadata["question"] = value
                    return metadata
            except Exception:
                pass
            position += len(marker)
    return metadata

try:
    nav_data = ss_graphql(
        "CodingNavigation",
        SS_NAV_QUERY,
        {
            "codeType": 1,
            "q": None,
            "curatedFilter": None,
            "isFreemium": None,
            "userSolutionState": None,
            "companies": [],
            "industries": [],
            "topics": [],
            "jobPositions": [],
            "difficulties": [],
            "hasVideoSolution": None,
            "isBookmarked": None,
            "orderField": None,
        },
    )

    all_edges = nav_data.get("questions", {}).get("edges", [])
    total_found = len(all_edges)
    edges = all_edges
    if SS_MAX_QUESTIONS > 0:
        edges = edges[:SS_MAX_QUESTIONS]
    print(f"=> StrataScratch tìm thấy: {total_found} bài")
    if SS_MAX_QUESTIONS > 0:
        print(f"=> Chế độ chạy thử: xử lý {len(edges)} bài đầu tiên")

    difficulty_map = {1: "Easy", 2: "Medium", 3: "Hard"}
    crawled_success = 0
    skipped_no_content = 0

    for idx, edge in enumerate(edges, start=1):
        node = edge.get("node") or {}
        slug = node.get("slug")
        if not slug:
            continue

        try:
            layout_data = ss_graphql(
                "CodingQuestionLayout",
                SS_LAYOUT_QUERY,
                {"slug": slug, "codeType": 1},
            )
            q = layout_data.get("educationalQuestion") or {}

            q_id = str(q.get("id") or node.get("id") or "")
            title = q.get("questionShort") or node.get("title") or slug.replace("-", " ").title()
            difficulty = difficulty_map.get(q.get("difficulty"), str(q.get("difficulty") or "Unknown"))
            schema_info = ss_schema_to_text(q.get("tables"))

            document_metadata = {}
            try:
                page = ss_session.get(
                    f"{SS_BASE}/coding/{slug}",
                    headers={"user-agent": ss_headers["user-agent"], "referer": SS_BASE + "/coding?code_type=1"},
                    timeout=20,
                )
                if page.status_code == 200:
                    document_metadata = ss_extract_document_metadata(page.text, slug)
                else:
                    preview = (page.text or "")[:180].replace("\n", " ")
                    print(f"!! [StrataScratch] Document {slug} HTTP {page.status_code}: {preview}")
            except Exception as page_error:
                print(f"!! [StrataScratch] Không lấy được document {slug}: {page_error}")

            full_question = str(document_metadata.get("question") or "").strip()
            cleaned_question = clean_text_single_line(full_question)
            locked_markers = (
                "this question is part of a paid plan",
                "upgrade to access this question",
                "subscribe to access this question",
            )
            normalized_question = cleaned_question.casefold()
            if (
                not cleaned_question
                or normalized_question == title.strip().casefold()
                or any(marker in normalized_question for marker in locked_markers)
            ):
                skipped_no_content += 1
                print(f"SKIP [NO FULL QUESTION]: {q_id} - {title}")
                time.sleep(0.10)
                continue

            content = cleaned_question

            solution_code = ""
            walkthrough = ""
            try:
                solution_data = ss_graphql(
                    "Solution",
                    SS_SOLUTION_QUERY,
                    {"slug": slug, "codeType": 1, "isDebug": False},
                )
                solution_question = solution_data.get("educationalQuestion") or {}
                official_solution = solution_question.get("officialOrRecommendedSolution") or {}
                solution_code = str(official_solution.get("code") or "").strip()
                walkthrough = str(solution_question.get("walkthrough") or "").strip()
            except Exception as solution_error:
                print(f"!! [StrataScratch] Không lấy được solution {slug}: {solution_error}")

            solution_source = solution_code or walkthrough
            detected_features = detect_sql_features(solution_source)
            if detected_features:
                technique = map_primary_technique(detected_features)
                keywords = features_to_keywords(detected_features)
            else:
                technique = classify_sql_technique(title, content)
                keywords = extract_keywords_exact(title, content)

            master_dataset.append({
                "id": f"SS-SQL-{q_id}",
                "nguồn": "StrataScratch",
                "đề bài": title,
                "nội dung": content,
                "bối cảnh": infer_business_context(title, content),
                "thể loại bài": difficulty,
                "kỹ thuật sử dụng": technique,
                "database_schema": schema_info,
                "từ khoá": keywords,
            })
            crawled_success += 1

            print(
                f"-> [StrataScratch] [{idx:03d}/{len(edges):03d}] "
                f"#{q_id:<6} {title[:32]:<32} | {difficulty:<6} | {schema_info[:45]}"
            )

        except Exception as item_error:
            print(f"!! [StrataScratch] Lỗi bài {slug}: {item_error}")

        time.sleep(0.10)

    print(f"=> Crawl thành công: {crawled_success} bài")
    print(f"=> Skip paid/no content: {skipped_no_content} bài")

except Exception as e:
    print(f"Lỗi StrataScratch: {e}")


# =========================================================================

# NGUỒN 3: DATALEMUR
# =========================================================================
print("\n=== [3/4] ĐANG CÀO TOÀN BỘ BÀI TẬP DATALEMUR ===")
dl_session = cffi_requests.Session(impersonate="chrome120")
dl_headers = {
    "accept": "*/*",
    "referer": "https://datalemur.com/questions",
    "x-nextjs-data": "1"
}

try:
    dl_resp = dl_session.get("https://datalemur.com/questions", timeout=15)
    soup = BeautifulSoup(dl_resp.text, 'html.parser')
    next_data_script = soup.find('script', id='__NEXT_DATA__')
    if not next_data_script or not next_data_script.string:
        raise RuntimeError("Không tìm thấy __NEXT_DATA__ của DataLemur")
    BUILD_ID = json.loads(next_data_script.string).get("buildId")
    if not BUILD_ID:
        raise RuntimeError("Không tìm thấy buildId hiện tại của DataLemur")
    links = soup.find_all('a', href=re.compile(r'^/questions/[a-zA-Z0-9-]+$'))
    all_slugs = sorted(set([a['href'].replace('/questions/', '') for a in links if a['href'] != '/questions']))
    candidate_slugs = [s for s in all_slugs if not s.startswith('python-') and not s.startswith('r-') and not s.startswith('generative-')]
    
    print(f"=> Đã tìm thấy {len(candidate_slugs)} bài tiềm năng trên DataLemur.")
    datalemur_crawled = 0
    datalemur_skipped_non_sql = 0
    
    for idx, slug in enumerate(candidate_slugs):
        detail_url = f"https://datalemur.com/_next/data/{BUILD_ID}/questions/{slug}.json?questionSlug={slug}"
        d_res = dl_session.get(detail_url, headers=dl_headers, timeout=10)
        
        if d_res.status_code == 200:
            json_data = d_res.json()
            queries = json_data.get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
            q_data = {}
            for query in queries:
                candidate = query.get("state", {}).get("data", {})
                if isinstance(candidate, dict) and candidate.get("title") and candidate.get("description"):
                    q_data = candidate
                    break
            if not q_data:
                q_data = json_data.get("pageProps", {}).get("question", {})

            if q_data:
                category = str(q_data.get("category") or "").strip()
                if category.casefold() != "sql":
                    datalemur_skipped_non_sql += 1
                    print(
                        f"SKIP [DataLemur non-SQL]: {slug} "
                        f"| category={category or 'missing'}"
                    )
                    time.sleep(0.08)
                    continue

                title = q_data.get("title") or slug.replace('-', ' ').title()
                company = q_data.get("company", "Tech")
                diff = q_data.get("difficulty", "Medium")
                raw_text = q_data.get("description", "")
                
                schema_part = raw_text
                for stop_w in ['### Example Input:', 'Example Input:', '## Solution']:
                    if stop_w in schema_part:
                        schema_part = schema_part.split(stop_w)[0]
                
                table_sections = re.split(r'[`\*]*([a-zA-Z0-9_]+)[`\*]*\s+Table:', schema_part, flags=re.I)
                schemas = []
                if len(table_sections) > 1:
                    for i in range(1, len(table_sections), 2):
                        tb_name = table_sections[i].strip()
                        tb_content = table_sections[i+1]
                        md_rows = re.findall(r'\|\s*([a-zA-Z0-9_]+)\s*\|\s*([a-zA-Z0-9_()]+)\s*\|', tb_content)
                        valid_cols = [
                            f"{c.strip()} {t.strip().lower()}" 
                            for c, t in md_rows 
                            if t.strip().lower() in VALID_SQL_TYPES and c.strip().lower() not in ['column_name', 'type']
                        ]
                        if valid_cols:
                            schemas.append(f"{tb_name} ({', '.join(valid_cols)})")

                final_schema = " | ".join(schemas) if schemas else "Schema mô tả trong đề"
                clean_desc = clean_text_single_line(schema_part)
                
                if len(clean_desc) > 30:
                    context = infer_business_context(title, clean_desc, company)
                    proper_query = str(
                        q_data.get("properQuery") or q_data.get("mysqlProperQuery") or ""
                    ).strip()
                    solution_explanation = str(
                        q_data.get("solutionExplanation")
                        or q_data.get("mysqlSolutionExplanation")
                        or ""
                    ).strip()
                    solution_source = proper_query or solution_explanation
                    detected_features = detect_sql_features(solution_source)
                    if detected_features:
                        technique = map_primary_technique(detected_features)
                        keywords = features_to_keywords(detected_features)
                    else:
                        technique = classify_sql_technique(title, clean_desc)
                        keywords = extract_keywords_exact(title, clean_desc)
                    
                    master_dataset.append({
                        "id": f"DL-SQL-{len(master_dataset)+1:04d}",
                        "nguồn": "DataLemur",
                        "đề bài": title,
                        "nội dung": clean_desc,
                        "bối cảnh": context,
                        "thể loại bài": diff,
                        "kỹ thuật sử dụng": technique,
                        "database_schema": final_schema,
                        "từ khoá": keywords
                    })
                    datalemur_crawled += 1
                    print(f"-> [DataLemur] {title[:20]:<20} | Schema: {final_schema[:35]}...")
        time.sleep(0.08)
    print(f"=> DataLemur SQL crawl thành công: {datalemur_crawled} bài")
    print(f"=> DataLemur skip non-SQL: {datalemur_skipped_non_sql} bài")
except Exception as e:
    print(f"Lỗi DataLemur: {e}")

# =========================================================================
# NGUỒN 4: HACKERRANK
# =========================================================================
print("\n=== [4/4] ĐANG CÀO TOÀN BỘ BÀI TẬP HACKERRANK ===")
hr_session = cffi_requests.Session(impersonate="chrome120")
try:
    ocr_reader = easyocr.Reader(['en'], gpu=False)
    hr_url = "https://www.hackerrank.com/rest/contests/master/tracks/sql/challenges?offset=0&limit=100"
    hr_res = hr_session.get(hr_url, timeout=15)
    
    if hr_res.status_code == 200:
        hr_challenges = hr_res.json().get('models', [])
        print(f"=> Đã tìm thấy {len(hr_challenges)} bài SQL thực tế từ HackerRank.")
        
        for idx, ch in enumerate(hr_challenges):
            slug = ch.get('slug')
            title = ch.get('name')
            diff = ch.get('difficulty_name', 'Easy')
            
            det_url = f"https://www.hackerrank.com/rest/contests/master/challenges/{slug}"
            det_r = hr_session.get(det_url, timeout=10)
            
            if det_r.status_code == 200:
                raw_html = det_r.json().get('model', {}).get('body_html', '')
                soup = BeautifulSoup(raw_html, 'html.parser')
                
                final_schema = extract_hackerrank_schema(raw_html, soup, ocr_reader, hr_session)
                clean_desc = clean_text_single_line(raw_html)
                
                context = infer_business_context(title, clean_desc)
                technique = classify_sql_technique(title, clean_desc)
                keywords = extract_keywords_exact(title, clean_desc)
                
                master_dataset.append({
                    "id": f"HR-SQL-{len(master_dataset)+1:04d}",
                    "nguồn": "HackerRank",
                    "đề bài": title,
                    "nội dung": clean_desc,
                    "bối cảnh": context,
                    "thể loại bài": diff,
                    "kỹ thuật sử dụng": technique,
                    "database_schema": final_schema,
                    "từ khoá": keywords
                })
                print(f"-> [HackerRank] {title[:20]:<20} | Schema: {final_schema[:35]}...")
            time.sleep(0.08)
except Exception as e:
    print(f"Lỗi HackerRank: {e}")

# =========================================================================
# 5. XUẤT RA FILE EXCEL HỢP NHẤT
# =========================================================================
output_filename = "Master_SQL_Dataset_All_Sources_2_1.xlsx"
df_master = pd.DataFrame(master_dataset)

ordered_columns = [
    "id", "nguồn", "đề bài", "nội dung", "bối cảnh", 
    "thể loại bài", "kỹ thuật sử dụng", "database_schema", "từ khoá"
]
df_master = df_master[ordered_columns]

try:
    df_master.to_excel(output_filename, index=False)
except PermissionError:
    output_filename = f"Master_SQL_Dataset_All_Sources_{int(time.time())}.xlsx"
    df_master.to_excel(output_filename, index=False)

print("\n" + "=" * 75)
print(f"=> HỢP NHẤT THÀNH CÔNG! Đã lưu tổng cộng {len(df_master)} bài tập vào file '{output_filename}'")
print("=" * 75)
