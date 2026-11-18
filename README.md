# SQLArena AI — Hệ Thống Tự Động Sinh Đề, Kiểm Định Kép & Chấm Thi SQL Trên PostgreSQL 17

> **Đồ Án Học Viện Công Nghệ Bưu Chính Viễn Thông (PTIT)**  
> Kiến trúc **1 Cổng Đăng Nhập Thống Nhất · Phân Quyền & Chia Đường Dẫn Theo Vai Trò (`RBAC`)**, tích hợp **`https://apithat.dev`** và dữ liệu thực thi 100% trên **PostgreSQL 17**.

![Kiến trúc tổng thể SQLArena AI](docs/diagrams/system-architecture.svg)

---

## 1. Kiến Trúc Đăng Nhập Tập Trung, Phân Quyền `RBAC` & Dữ Liệu Thật

1. **Một Cổng Web & Một Khung Đăng Nhập Thống Nhất (`http://localhost:3000`)**:
   - Toàn bộ người dùng (Sinh viên và Giảng viên/Quản trị viên) đăng nhập hoặc tự **Đăng ký** mới tại **cùng một giao diện duy nhất** (`http://localhost:3000/`). Không tách rời 2 form đăng nhập riêng, không bắt buộc phải gõ đường dẫn `/admin` trước mới đăng nhập được tài khoản Quản trị.
   - Mọi mật khẩu đều xác thực qua băm mật khẩu chuẩn **`PBKDF2-HMAC-SHA256`** kết hợp JWT và bảng phân quyền `live.roles` trong PostgreSQL (tuyệt đối không fix cứng quyền hạn hay mật khẩu mặc định trong mã nguồn).

2. **Tự Động Chia Đường Dẫn (`Path`) Theo Vai Trò (`Role`) Sau Khi Đăng Nhập**:
   | Vai trò (`live.roles`) | Đường dẫn được cấp quyền | Mô tả chức năng |
   | :--- | :--- | :--- |
   | **`learner`** *(Học viên)* | `/` · `/progress` · `/leaderboard` | Làm bài SQL Sandbox (`/`), theo dõi Tiến độ & lịch sử nộp bài (`/progress`), xem Bảng xếp hạng (`/leaderboard`). Không hiển thị nút Quản trị; nếu truy cập `/admin` sẽ tự động chuyển về `/` và bị chặn `403` tại API. |
   | **`admin`** *(Quản trị viên)* | `/` · `/progress` · `/leaderboard` · **`/admin`** | Giữ **đầy đủ** toàn bộ tính năng làm bài, tiến độ, xếp hạng của người dùng, **cộng thêm** đường dẫn `/admin` (Quản lý người dùng & cấp quyền động, Sinh đề AI theo từng kỹ năng `S1–S6`, Duyệt đề, Bộ đề tuần & Nhóm đề, Ngân hàng đề, Cấu hình). |

3. **Dữ Liệu Khởi Tạo (`Seed Data`) Thực Thi Thật 100% Trên PostgreSQL 17**:
   - Tập dữ liệu doanh nghiệp `enterprise_db` gồm **13 bảng có quan hệ khóa ngoại thực tế** (nhân sự, khách hàng, sản phẩm, đơn hàng, thanh toán, hoàn tiền, kho vận).
   - Khi chạy `seed-demo` lần đầu sau khi `git clone`, toàn bộ **50 câu hỏi gốc (`ENT-001..ENT-050`)**, bộ kiểm thử `live.test_cases`, các bản nháp mẫu và lịch sử nộp bài đều được **thực thi SQL trực tiếp trên `enterprise_db`** để sinh kết quả, số dòng và thời gian chạy (`runtime_ms`) thực tế — không dùng dữ liệu giả lập cứng.

4. **Kiểm Định Kép Hiệu Chỉnh (`Calibrated Dual-Model Verification` qua `apithat.dev`)**:
   - **Model A** sinh đề tiếng Việt theo số lượng riêng từng nhóm kỹ năng (`S1–S6`).
   - **Model B** giải độc lập `k = 3` lần trên giao dịch chỉ đọc (`sqlarena_ai_ro`), kiểm tra cú pháp AST `pglast`, đồng thuận kết quả và `ORDER BY`. Đề đạt `approved` tự lên kệ làm bài, đồng thời hỗ trợ đảo chiều `approved <-> needs_human` và gom nhóm đăng hàng loạt.

![Quy trình Kiểm định Kép & Xuất bản Linh hoạt](docs/diagrams/dual-model-pipeline.svg)

---

## 2. Cấu Trúc Thư Mục (`MyKit v3.15`)

```text
sqlarena-ai/
├── AGENTS.md / CLAUDE.md          # Sổ tay vận hành & lệnh kiểm chứng (<100 dòng)
├── Dockerfile                     # Python 3.12 non-root runtime (UID 10001)
├── docker-compose.yml             # Cụm containers (Frontend Nginx, FastAPI, Worker, PostgreSQL 17)
├── scripts/
│   ├── deploy-vps.sh              # Triển khai 1 lệnh bằng Docker (Local / VPS) + Rollback LKG
│   └── set-apithat-key.sh         # Nạp khóa https://apithat.dev/keys bảo mật Secret-Blind
├── backend/                       # FastAPI + SQLAlchemy 2.x Core + Alembic (0001..0005) + 61 Pytest
├── ai/                            # Động cơ Model A, Model B, AST Validator (pglast) + 104 Unittests
├── frontend/                      # Next.js 16 App Router (/, /progress, /leaderboard, /admin) + DESIGN.md
├── postgre/                       # Kịch bản khởi tạo PostgreSQL 17 & tập dữ liệu enterprise_db
├── question_create/               # Quy tắc 6 nhóm kỹ năng S1–S6 & 5 miền nghiệp vụ
└── docs/                          # Đặc tả LAW.md, ARCHITECTURE.md, WBS.md, DECISIONS.md, REVIEW.md, OPENAPI_V1.md
```

---

## 3. Hướng Dẫn `git clone` & Khởi Chạy Nhanh

### Bước 1: Clone dự án & cấu hình khóa `https://apithat.dev/keys` (tùy chọn khi dùng Sinh đề AI)
```bash
git clone https://github.com/Hungnn1904/sqlarena-ai.git
cd sqlarena-ai
./scripts/set-apithat-key.sh
```
*(Hoặc đăng nhập quyền Admin rồi cập nhật khóa trực tiếp tại `/admin` -> tab **Sinh đề AI** / **Cấu hình**).*

### Bước 2: Khởi chạy toàn bộ hệ thống bằng Docker
```bash
./scripts/deploy-vps.sh
```
- Mở trình duyệt tại: **`http://localhost:3000`** *(nếu cổng `3000` trên máy đang bận bởi ứng dụng khác, script tự động chuyển sang cổng trống như `http://localhost:3005` và in rõ trên màn hình)*.
- **Cách đăng nhập & sử dụng sau khi clone**:
  - **Tự đăng ký mới**: Bấm tab **Đăng ký** ngay tại `http://localhost:3000` để tạo tài khoản Học viên mới (`role = learner`).
  - **Tài khoản khởi tạo sẵn từ `seed.py`** *(có thể đổi qua biến môi trường `SEED_ADMIN_*` / `SEED_LEARNER_*` hoặc quản lý trực tiếp trong tab **Người dùng** tại `/admin`)*:
    - Quản trị viên (`role = admin`, vào được cả `/`, `/progress`, `/leaderboard` và `/admin`): `admin` / `admin123`
    - Học viên khởi tạo mẫu (`role = learner`, vào `/`, `/progress`, `/leaderboard`): `hocvien` / `hocvien123`

---

## 4. Lệnh Kiểm Chứng Tự Động (`All Exit 0`)

- **Backend Pytest (61 tests trên PostgreSQL 17 thật)**: `(cd backend && ../.venv/bin/pytest -q)`
- **AI Dual-Model & AST Unittests (104 tests)**: `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)`
- **Frontend Static Export Build**: `(cd frontend && npm run build)`
- **Hồ sơ cổng kiểm định chi tiết**: Xem tại [`docs/WBS.md`](docs/WBS.md) và [`docs/REVIEW.md`](docs/REVIEW.md).
