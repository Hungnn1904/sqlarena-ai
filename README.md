# SQLArena AI — Question Generator Pipeline

Hệ thống tự động sinh câu hỏi SQL theo độ khó bằng AI, với pipeline 7 bước: taxonomy → target selection → planning → generation → clarity check → execution verify → lưu vào question bank.

> Đã chạy local, chưa test trên Docker.

---

## Cấu trúc dự án

```
sqlarena-ai-staging/
├── pipeline.py          # Pipeline chính: 7 bước sinh + validate câu hỏi
├── main.py              # FastAPI entrypoint, expose POST /generate
├── llm_gateway.py       # Giao tiếp với Ollama hoặc Gemini
├── question_planner.py  # Bước 3: tạo blueprint trước khi sinh câu hỏi
├── question_bank.py     # Lưu trữ câu hỏi vào SQLite
├── clarity_checker.py   # Bước 5: kiểm tra câu hỏi có rõ nghĩa không
├── execution_engine.py  # Bước 6: chạy SQL thật trên sandbox SQLite
├── taxonomy.py          # Bước 1: danh sách topic + skill SQL
├── schema_loader.py     # Load + generate DDL/seed từ schema
├── retry_policy.py      # Logic retry + archive fallback
├── run_experiments.py   # Script đo tỉ lệ valid
├── schema.json          # Định nghĩa schema DB dùng để sinh câu hỏi
├── requirements.txt     # Dependencies
├── Dockerfile
├── docker-compose.yml
├── .env.example         # Template biến môi trường
└── Output/              # Output JSON theo ngày
    └── YYYY-MM-DD/
        └── sql_questions_*.json
```

---

## Kiến trúc pipeline

```
POST /generate  (hoặc python pipeline.py trực tiếp)
       │
       ▼
Step 1 — Taxonomy Loader
       Nạp danh sách topic SQL và skill cần cover
       │
       ▼
Step 2 — Target Selector
       Chọn topic + difficulty dựa trên stats hiện tại
       │
       ▼
Step 3 — Question Planner  [LLM call]
       Sinh blueprint: intent, target_skill, trap_strategy
       │
       ▼
Step 4 — Question Generator  [LLM call]
       Sinh schema_sql, seed_sql, question_text, answer_sql
       │
       ▼
Step 5 — Clarity Check
       Kiểm tra câu hỏi có rõ nghĩa, có action word không
       │
       ▼
Step 6 — Execution Verify
       Chạy schema + seed + answer_sql thật trên SQLite sandbox
       │
       ▼
Step 7 — Save to Question Bank
       Lưu vào SQLite, trạng thái pending_review
```

---

## Cài đặt

### Yêu cầu

- Python 3.11+
- Ollama đang chạy local **hoặc** Gemini API key

### 1. Cài thư viện

```bash
pip install -r requirements.txt
```

### 2. Cấu hình `.env`

```bash
cp .env.example .env
```

---

## Cấu hình LLM

Chỉnh `.env` theo provider muốn dùng. Không cần sửa code.

### Dùng Ollama (khuyến nghị cho local)

```dotenv
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
MODEL_NAME=qwen2.5-coder:3b

ENV=local
```

Pull model trước khi chạy:

```bash
ollama pull qwen2.5-coder:3b
```

> **Lưu ý phần cứng:** `qwen2.5-coder:3b` cần ~4GB VRAM hoặc ~8GB RAM để chạy CPU. Đây là model nhỏ nhất cho ra kết quả ổn định. `llama3` không khuyến nghị — JSON following kém, hay fail.

### Dùng Gemini (nếu không có GPU)

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
MODEL_NAME=gemini-2.0-flash

ENV=local
```

> **Lưu ý rate limit:** `gemini-2.5-flash` free tier giới hạn 5 req/phút — không phù hợp cho pipeline batch. Dùng `gemini-2.0-flash` (15 req/phút) hoặc thêm `INTER_QUESTION_DELAY=15` vào `.env`.

---

## Chạy

### Chạy pipeline trực tiếp

```bash
python pipeline.py
```

### Chạy qua API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"specs": ["easy", "medium", "hard"]}'
```

Tài liệu API tương tác (Swagger UI): `http://localhost:8000/docs`

---

## Chạy bằng Docker

```bash
docker-compose up --build
```

> Ollama trên host được truy cập qua `host.docker.internal:11434` — đã cấu hình sẵn trong `docker-compose.yml`. Docker không giúp chạy model lớn hơn — bottleneck vẫn là phần cứng máy host.

---

## Output

Mỗi lần chạy pipeline sinh file JSON tại:

```
Output/YYYY-MM-DD/sql_questions_easy_medium_hard_HHMMSS.json
```

Câu hỏi sau khi validate được lưu vào `data/questions.db` (SQLite) với trạng thái `pending_review`.

---

## Schema mặc định

Định nghĩa trong `schema.json`, được load qua `schema_loader.py`:

| Table | Columns |
|---|---|
| `employees` | id, name, department_id, role |
| `departments` | id, name |
| `products` | product_id, category_id, price, stock |
| `sales` | sale_id, product_id, quantity |
| `inventory` | product_id, quantity |

---

## Dependencies

| Package | Mục đích |
|---|---|
| `fastapi` + `uvicorn` | Web API |
| `httpx` | Gọi Ollama API |
| `google-genai` | Gọi Gemini API |
| `sqlglot` | Parse & validate SQL syntax |
| `python-dotenv` | Load `.env` |
| `prefect` | Pipeline orchestration |
| `pydantic` | Data validation |

---

## Kiểm thử pipeline & đo tỉ lệ valid

Pipeline được tối ưu để tolerant với output của LLM: tự động điền giá trị mặc định nếu thiếu key, chấp nhận output không hoàn hảo, chỉ cần valid rate > 60%.

Script `run_experiments.py` cho phép chạy thử nghiệm sinh câu hỏi liên tiếp và đo tỉ lệ valid:

```bash
python run_experiments.py
```

Script chạy 10 lần (hoặc số lần chỉnh trong file), mỗi lần sinh 1 câu hỏi (dễ), tổng hợp số câu valid và tỉ lệ thành công. Kết quả in ra màn hình và lưu vào `experiment_results.json`.

Ví dụ output:

```
=== Summary ===
Trials: 10
Total generated: 10
Total valid: 8
Total failed: 2
Valid rate (valid/generated): 80.00%
```

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Giải pháp |
|---|---|---|
| `LLM JSON missing keys` liên tục | Model quá yếu (`llama3`) hoặc `num_ctx` nhỏ | Dùng `qwen2.5-coder:3b`, `num_ctx=8192` |
| `no such column: x` ở Step 6 | LLM hallucinate schema | Model yếu, thử lại hoặc đổi model |
| `429 RESOURCE_EXHAUSTED` (Gemini) | Vượt rate limit free tier | Thêm `INTER_QUESTION_DELAY=15` hoặc dùng `gemini-2.0-flash` |
| `404 NOT_FOUND` (Gemini 2.5) | Model chỉ có trên `v1alpha` | Đã fix trong `llm_gateway.py` — update file nếu dùng bản cũ |
| Ollama không kết nối | Service chưa chạy hoặc sai host | Chạy `ollama serve`, kiểm tra `OLLAMA_HOST` |
| `ValueError: No JSON object found` | API lỗi ở Step 3 không được catch | Update `pipeline.py` lên bản mới nhất |
| Clarity check reject oan | Action word list quá hẹp | Update `clarity_checker.py` lên bản mới nhất |

---

## Scope hiện tại

Repo này là **prototype** cho subsystem AI question generation. Chưa bao gồm:

- Auth / multi-tenant
- Judge service đa DB (MySQL, PostgreSQL, SQL Server)
- AI feedback engine
- Battle Royale / Social / Achievement
- Review queue thực sự
- Enterprise API

Xem `docs.md` để hiểu bức tranh lớn hơn của SQLArena platform.