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
    └── YYYY-MM-DD/
        └── sql_questions_*.json
```

---

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
```

---

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

### Yêu cầu

- Python 3.11+
- [Ollama](https://ollama.com) đang chạy local với model đã pull sẵn (mặc định: `llama3`)

### 1. Cài thư viện

```bash
pip install -r requirements.txt
```

### 2. Cấu hình `.env`

Tạo file `.env` từ template:

```bash
cp .env.example .env
```

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

```bash
python pipeline.py
```

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

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"specs": ["easy", "medium", "hard"]}'
```

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
