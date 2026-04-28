<<<<<<< HEAD
# SQLArena AI Question Generator Pipeline

Hệ thống tự động sinh câu hỏi SQL theo độ khó bằng AI (Ollama/LLaMA), được xây dựng với **FastAPI** + **Prefect** + **sqlglot**, hỗ trợ chạy local hoặc qua Docker.

---

## 📁 Cấu trúc dự án

```
PIPELINE/
├── main.py              # FastAPI entrypoint, expose /generate API
├── pipeline.py          # Prefect flow: sinh câu hỏi → validate SQL
├── llm_gateway.py       # Giao tiếp với Ollama LLM
├── schema.json          # Schema DB dùng để sinh câu hỏi
├── requirements.txt     # Các thư viện Python cần thiết
├── Dockerfile           # Build Docker image
├── docker-compose.yml   # Chạy service qua Docker Compose
├── .env                 # Biến môi trường (không commit)
├── .env.example         # Template biến môi trường
└── Output/              # Kết quả sinh ra, phân theo ngày
=======
# SQLArena AI — Question Generator Pipeline

Hệ thống tự động sinh câu hỏi SQL theo độ khó bằng AI, với pipeline 7 bước: taxonomy → target selection → planning → generation → clarity check → execution verify → lưu vào question bank.

---

Đã chạy local, chưa test trên docker

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
├── schema.json          # Định nghĩa schema DB dùng để sinh câu hỏi
├── requirements.txt     # Dependencies
├── Dockerfile
├── docker-compose.yml
├── .env.example         # Template biến môi trường
└── Output/              # Output JSON theo ngày
>>>>>>> 6a4affa (Initial push: tolerant pipeline, experiment runner, docs update)
    └── YYYY-MM-DD/
        └── sql_questions_*.json
```

---

<<<<<<< HEAD
## ⚙️ Kiến trúc hệ thống

```
POST /generate
     │
     ▼
FastAPI (main.py)
     │
     ▼
Prefect Flow (pipeline.py)
     │
     ├── [Task] generator(spec)
     │       └── Gửi prompt → LLMGateway → Ollama → trả raw JSON
     │
     ├── [Task] validate(raw)
     │       └── Extract SQL → parse bằng sqlglot
     │
     └── Lưu kết quả vào Output/YYYY-MM-DD/*.json
=======
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
>>>>>>> 6a4affa (Initial push: tolerant pipeline, experiment runner, docs update)
```

---

<<<<<<< HEAD
## 🗄️ Database Schema

Schema được định nghĩa trong `schema.json` và nhúng vào prompt khi sinh câu hỏi:

| Table         | Columns                                              |
|---------------|------------------------------------------------------|
| `employees`   | id, name, department_id, role                        |
| `departments` | id, name                                             |
| `products`    | product_id, category_id, price, stock                |
| `sales`       | sale_id, product_id, quantity                        |
| `inventory`   | product_id, quantity                                 |

---

## 🔧 Cài đặt & Chạy local
=======
## Cài đặt
>>>>>>> 6a4affa (Initial push: tolerant pipeline, experiment runner, docs update)

### Yêu cầu

- Python 3.11+
<<<<<<< HEAD
- [Ollama](https://ollama.com) đang chạy local với model đã pull sẵn (mặc định: `llama3`)
=======
- Ollama đang chạy local **hoặc** Gemini API key
>>>>>>> 6a4affa (Initial push: tolerant pipeline, experiment runner, docs update)

### 1. Cài thư viện

```bash
pip install -r requirements.txt
```

### 2. Cấu hình `.env`

<<<<<<< HEAD
Tạo file `.env` từ template:

=======
>>>>>>> 6a4affa (Initial push: tolerant pipeline, experiment runner, docs update)
```bash
cp .env.example .env
```

<<<<<<< HEAD
Chỉnh sửa nội dung:

```env
OLLAMA_HOST=http://localhost:11434
MODEL_NAME=llama3
AI_PROVIDER=ollama
```

### 3. Pull model Ollama (nếu chưa có)

```bash
ollama pull llama3
```

### 4. Chạy server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Chạy pipeline trực tiếp (không cần API)
=======
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
>>>>>>> 6a4affa (Initial push: tolerant pipeline, experiment runner, docs update)

```bash
python pipeline.py
```

<<<<<<< HEAD
---

## 🐳 Chạy bằng Docker

### Yêu cầu

- Docker + Docker Compose
- Ollama chạy trên máy host

### Build & start

```bash
docker-compose up --build
```

> Ollama trên host sẽ được truy cập qua `host.docker.internal:11434` — đã cấu hình sẵn trong `docker-compose.yml`.

---

## 🚀 Sử dụng API

### Endpoint: `POST /generate`

**Request body:**

```json
{
  "specs": ["easy", "medium", "hard"]
}
```

- `specs`: danh sách độ khó muốn sinh. Mặc định: `["easy", "medium", "hard"]`

**Ví dụ với curl:**

=======
### Chạy qua API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

>>>>>>> 6a4affa (Initial push: tolerant pipeline, experiment runner, docs update)
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"specs": ["easy", "medium", "hard"]}'
```

<<<<<<< HEAD
**Response mẫu:**

```json
{
  "results": [
    {
      "spec": "easy",
      "valid": true,
      "raw": {
        "question": "List all employees in the Sales department.",
        "sql": "SELECT e.name FROM employees e JOIN departments d ON e.department_id = d.id WHERE d.name = 'Sales'",
        "difficulty": "easy"
      }
    }
  ]
}
```

### Swagger UI

Truy cập tài liệu API tương tác tại:

```
http://localhost:8000/docs
```

---

## 📦 Output

Mỗi lần chạy pipeline sẽ tạo file JSON tại:

```
Output/YYYY-MM-DD/sql_questions_<specs>_<HHMMSS>.json
```

Ví dụ:

```
Output/2026-04-26/sql_questions_easy_medium_hard_155056.json
```

---

## 🧩 Thư viện sử dụng

| Package       | Mục đích                          |
|---------------|-----------------------------------|
| `fastapi`     | Web API framework                 |
| `uvicorn`     | ASGI server                       |
| `prefect`     | Orchestrate pipeline tasks/flows  |
| `httpx`       | HTTP client gọi Ollama API        |
| `sqlglot`     | Parse & validate SQL syntax       |
| `python-dotenv` | Load biến môi trường từ `.env` |

---

## 🐛 Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| Ollama không kết nối được | Kiểm tra `OLLAMA_HOST` trong `.env`, đảm bảo Ollama đang chạy |
| Model không tìm thấy | Chạy `ollama pull llama3` |
| LLM trả về lỗi / timeout | Tăng `timeout` trong `llm_gateway.py`, hoặc giảm `num_ctx` |
| Docker không gọi được Ollama | Đảm bảo dùng `host.docker.internal` thay vì `localhost` |
| SQL không hợp lệ (`valid: false`) | LLM sinh ra SQL sai cú pháp — thử lại hoặc điều chỉnh prompt |
=======
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

## Troubleshooting

| Triệu chứng | Nguyên nhân | Giải pháp |
|---|---|---|
| `LLM JSON missing keys` liên tục | Model quá yếu (llama3) hoặc `num_ctx` nhỏ | Dùng `qwen2.5-coder:3b`, `num_ctx=8192` |
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


---

## ⚡️ Kiểm thử pipeline & đo tỉ lệ valid

Pipeline đã được tối ưu để tolerant hơn với output của LLM (tự động điền giá trị mặc định nếu thiếu key, chấp nhận output không hoàn hảo, chỉ cần valid rate > 60%).

### Chạy thử nghiệm sinh câu hỏi liên tiếp

Đã có sẵn script `run_experiments.py` để chạy thử nghiệm sinh câu hỏi liên tiếp và đo tỉ lệ valid:

```bash
python run_experiments.py
```

Script sẽ chạy 10 lần (hoặc số lần bạn chỉnh trong file), mỗi lần sinh 1 câu hỏi (dễ), tổng hợp số câu valid và tỉ lệ thành công. Kết quả sẽ in ra màn hình và lưu vào file `experiment_results.json`.

**Ví dụ output:**

```
=== Summary ===
Trials: 10
Total generated: 10
Total valid: 8
Total failed: 2
Valid rate (valid/generated): 80.00%
```

### Hướng dẫn sử dụng nhanh

1. Đảm bảo đã cài đặt và cấu hình như hướng dẫn ở trên.
2. Chạy lệnh:
       ```bash
       python run_experiments.py
       ```
3. Xem kết quả tổng hợp trên terminal hoặc trong file `experiment_results.json`.

---

Xem `docs.md` để hiểu bức tranh lớn hơn của SQLArena platform.
>>>>>>> 6a4affa (Initial push: tolerant pipeline, experiment runner, docs update)
