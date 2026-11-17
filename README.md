# SQLArena AI — Hệ Thống Tự Động Sinh Đề, Kiểm Định Kép & Chấm Thi SQL Trên PostgreSQL 17

> **Đồ Án Tốt Nghiệp / Chuyên Đề Học Viện Công Nghệ Bưu Chính Viễn Thông (PTIT)**  
> Chuẩn hoá kiến trúc, kiểm chứng độc lập (`Hunter != Verifier`) và quy trình vận hành theo chuẩn **MyKit v3.15**.

![Kiến trúc tổng thể SQLArena AI](docs/diagrams/system-architecture.svg)

---

## 1. Bài Toán Đặt Ra & Đóng Góp Cốt Lõi Của Đồ Án

Trong đào tạo Cơ sở dữ liệu thực hành, việc ra đề SQL thủ công tốn nhiều công sức nhưng nếu dùng LLM sinh đề trực tiếp thì thường gặp **ảo giác đáp án (Hallucination)**: câu SQL mẫu lỗi cú pháp, trả về `0` dòng dữ liệu hoặc mâu thuẫn với yêu cầu tiếng Việt.

**SQLArena AI** giải quyết bài toán này qua **4 đóng góp kỹ thuật trọng tâm**:
1. **Kiến trúc Kiểm định Kép Độc Lập (`Generator != Blind Verifier`)**:
   - **Model A (Generator)** chỉ thiết kế kịch bản câu hỏi tiếng Việt trên lược đồ doanh nghiệp thực tế (`enterprise_db` — 13 bảng, `>13.400` bản ghi), tuyệt đối không được tự chèn đáp án.
   - **Model B (Blind Solver)** nhận đề bài tiếng Việt mà không biết metadata ẩn của Model A, giải độc lập `k = 3` lần trên PostgreSQL 17 chỉ đọc (`sqlarena_ai_ro`) qua bộ phân tích cú pháp `pglast` AST, đối chiếu đồng thuận kết quả và kiểm toán ngữ nghĩa.
2. **Cơ chế Kiểm duyệt Hiệu chỉnh (`Calibrated Approval`)**:
   - Giữ cứng 100% các chốt uy tín cốt lõi (chỉ đọc `SELECT`/`WITH`, chạy thật `row_count > 0`, `0` lời giải hợp lệ bất đồng kết quả, bắt buộc `ORDER BY` khi đề yêu cầu, chống trùng đề nguồn `>= 0.72`).
   - Loại bỏ các lỗi đánh rớt hình thức (khác tên biến alias tiếng Anh không nêu trong đề, chấp nhận `>= 2/3` mẫu đồng thuận tuyệt đối khi 1 mẫu vấp cú pháp JSON thoáng qua, tự chuẩn hoá khóa ngoại `FK` cho Model A).
3. **Không gian Gom Nhóm Kéo Thả & Phát Hành Nguyên Khối (`Question Groups`)**:
   - Đề sau khi duyệt nằm tại **Kho Đề Sẵn Sàng (`live.questions` trạng thái `ready`)**, không tự lộ lẻ tẻ ra màn hình học viên.
   - Giảng viên duyệt hàng loạt (`bulk-approve`), tự soạn đề thủ công hoặc kéo thả / tick chọn nhiều câu vào **Nhóm Đề (`live.question_groups`)**, sắp xếp thứ tự rồi bấm **1 nút phát hành toàn bộ nhóm** lên kệ làm bài trong 1 giao dịch nguyên tử (`SELECT ... FOR UPDATE`).
4. **Môi trường Học tập Thân thiện & Triển khai VPS Không Cần Tên Miền (`http://<VPS_IP>:3000`)**:
   - Tích hợp khóa chính `PK` / khóa ngoại `FK` trực quan, hiển thị cột đầu ra bắt buộc (`output_columns`), lưu nháp SQL theo từng bài, cho phép chú thích `-- comment` và trợ lý gợi ý `AI SQL Coach` + `EXPLAIN`.
   - Định tuyến cùng nguồn (`Same-Origin`) qua Nginx Reverse Proxy (`:3000/api/* -> backend:8000`), giúp chạy ngay trên mọi địa chỉ IP VPS chỉ với cổng `3000` mà không cần mua domain hay cấu hình CORS phức tạp.

![Quy trình Kiểm định Kép & Phát hành Nhóm đề](docs/diagrams/dual-model-pipeline.svg)

---

## 2. Cấu Trúc Thư Mục Chuẩn Polyrepo (`Chung vs Riêng`)

```text
sqlarena-ai/
├── AGENTS.md / CLAUDE.md          # Cẩm nang điều phối chuẩn MyKit v3.15 (<100 dòng)
├── Dockerfile                     # Multi-layer Python 3.12 non-root runtime (backend & worker)
├── docker-compose.yml             # Cụm 4 containers: postgres, backend, worker, frontend
├── scripts/
│   ├── deploy-vps.sh              # Triển khai 1 lệnh lên VPS không cần domain + Rollback LKG
│   └── set-apithat-key.sh         # Nạp khóa API Thật (apithat.dev/keys) bảo mật Secret-Blind
├── backend/                       # FastAPI + SQLAlchemy 2.x Core + Alembic (0001..0004) + 56 Pytest
├── ai/                            # Động cơ Model A, Model B, AST Validator (pglast) + 104 Unittests
├── frontend/                      # Next.js 16 Static Export + Nginx /api/ Proxy + DESIGN.md
├── postgre/                       # Kịch bản khởi tạo PostgreSQL 17 & tập dữ liệu enterprise_db
├── question_create/               # Quy tắc phân loại 6 nhóm kỹ năng S1–S6 & 5 miền nghiệp vụ
└── docs/                          # Bộ tài liệu chuẩn đồ án (Zero Markdown Sprawl)
    ├── LAW.md                     # Bất biến nghiệp vụ, bảo mật Read-Only Sandbox & 6 Invariants
    ├── ARCHITECTURE.md            # Kiến trúc runtime, tích hợp apithat.dev & Ma trận Edge Cases
    ├── WBS.md                     # Phân rã công việc theo pha (Agent + Skill + Gate)
    ├── DECISIONS.md               # Hồ sơ quyết định kiến trúc (ADR-001..ADR-004)
    ├── REVIEW.md                  # Bằng chứng kiểm định độc lập & Nhật ký kiểm toán UX người mới
    ├── api/OPENAPI_V1.md          # Hợp đồng REST API chuẩn duy nhất (SSOT)
    └── diagrams/*.svg             # Sơ đồ kiến trúc vector độ phân giải cao phục vụ báo cáo
```

---

## 3. Hướng Dẫn Cài Đặt, Kết Nối `apithat.dev` & Triển Khai VPS Từng Bước

### Bước 1: Kết nối khóa API từ `https://apithat.dev/keys` (Secret-Blind)
Dự án tích hợp trực tiếp cổng **API Thật (`https://apithat.dev/v1`)** với cơ chế tự động nhận diện model theo nhóm khóa (`gpt-5.6-sol`, `gpt-6.1-terra`, `gpt-6-sol`, `gpt-6-astra`, `claude-sonnet-5-5`...). Bạn có **2 cách an toàn** (không bao giờ phải dán khóa lộ liễu vào hội thoại hay commit lên Git):
- **Cách 1 — Qua dòng lệnh ẩn ký tự (Khuyên dùng trên máy chủ/VPS)**:
  ```bash
  ./scripts/set-apithat-key.sh
  ```
  *(Script sẽ hỏi khóa ở chế độ ẩn, kiểm tra `200 OK` trực tiếp với `https://apithat.dev/v1/models`, lưu quyền `600` vào `.env` / `backend/.env` và tự động nạp vào Docker).*
- **Cách 2 — Trực tiếp trên Giao diện Quản trị Web**:
  Đăng nhập quyền **Giảng viên / Admin** -> vào **Bước 1: Tạo đề mới** -> khung **Cổng AI Gateway (`apithat.dev/keys`)** -> dán khóa `sk-...` và bấm **Xác thực & Kích hoạt**.

### Bước 2: Chạy toàn bộ hệ thống bằng Docker (Local hoặc VPS không có Domain)
Trên VPS Ubuntu/Debian (chỉ cần mở cổng TCP `3000` trên tường lửa/UFW, cổng PostgreSQL được khóa nội bộ `127.0.0.1` an toàn tuyệt đối):
```bash
git clone https://github.com/Hungnn1904/sqlarena-ai.git
cd sqlarena-ai
./scripts/set-apithat-key.sh     # Dán khóa từ https://apithat.dev/keys
./scripts/deploy-vps.sh          # Tự build, chạy migrate, seed 50 đề nguồn & kiểm tra healthcheck
```
Sau khi hoàn tất, truy cập ngay từ bất kỳ máy tính hay điện thoại nào qua **`http://<IP_VPS>:3000`**:
- **Tài khoản Sinh viên mẫu**: `nguyen_ptit` / `demo123` (hoặc chọn nút 1 chạm trên màn hình chào mừng).
- **Tài khoản Giảng viên / Admin mẫu**: `admin` / `admin123` (hoặc đổi nhanh qua menu **Chế độ Demo**).
- **Kiểm tra trạng thái / Khôi phục bản ổn định trước (Rollback)**:
  ```bash
  ./scripts/deploy-vps.sh --status
  ./scripts/deploy-vps.sh --rollback
  ```

---

## 4. Kiểm Chứng Chất Lượng Tự Động (Bộ Test & MyKit Gates)

| Hạng mục kiểm thử | Lệnh thực thi | Kết quả xác nhận |
| :--- | :--- | :---: |
| **Backend Integration Suite (PostgreSQL 17 thật)** | `(cd backend && ../.venv/bin/pytest -q)` | **`56 passed`** |
| **AI Dual-Model & AST Guard Suite** | `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)` | **`104 tests OK`** |
| **Frontend Next.js 16 Static Build** | `(cd frontend && npm run build)` | **`PASS (dist/)`** |
| **MyKit Spec, TDD, Clean-Arch, Anti-Slop & DevOps Gates** | Xem danh sách lệnh tại [`docs/WBS.md`](docs/WBS.md) & [`docs/REVIEW.md`](docs/REVIEW.md) | **`0 FAIL (Exit 0)`** |
