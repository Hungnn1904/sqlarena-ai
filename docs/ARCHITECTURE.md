# Tài liệu Kiến trúc Hệ thống — SQLArena AI

## 1. Tổng quan Kiến trúc 4 Tầng (4-Layer Clean Architecture)

Hệ thống **SQLArena AI** được thiết kế theo mô hình kiến trúc tách lớp nghiêm ngặt trên nền tảng **PostgreSQL 17**, **FastAPI (Python)** và **Next.js 16 (React/TypeScript)**:

```
┌───────────────────────────────────────────────────────────────────────────┐
│ TẦNG 4: GIAO DIỆN NGƯỜI DÙNG & QUẢN TRỊ (Next.js 16 · React · Monaco)    │
│ • Làm bài (SQL Studio Workbench + Schema Explorer + AI SQL Coach)         │
│ • Tiến độ học tập (Ma trận năng lực S1–S6 · Chuỗi ngày luyện tập)         │
│ • Bảng xếp hạng (Tuần / Tháng / Toàn thời gian)                           │
│ • Quản trị (Sinh đề AI · Duyệt đề · Kho đề · Bộ đề tuần · Người dùng)    │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ REST API (/api/v1/*)
┌────────────────────────────────────▼──────────────────────────────────────┐
│ TẦNG 3: BACKEND ORCHESTRATION & SANDBOX ENGINE (FastAPI · SQLAlchemy)     │
│ • Auth & RBAC (JWT · Admin / Learner)                                     │
│ • Read-Only SQL Sandbox & Grading Engine (AST Guard + Result Diff)        │
│ • Background Generation Worker & Audit Log                                │
└─────────────────┬──────────────────────────────────────┬──────────────────┘
                  │                                      │
┌─────────────────▼──────────────────┐ ┌─────────────────▼──────────────────┐
│ TẦNG 2: DUAL-MODEL AI PIPELINE     │ │ TẦNG 1: DỮ LIỆU & SANDBOX DB       │
│ • Model A (Generator): llama3      │ │ • sqlarena_app (core / draft /     │
│ • Model B (Reviewer):              │ │   live schemas)                    │
│   qwen2.5-coder:7b (Blind 3/3)     │ │ • enterprise_db (13 bảng nghiệp vụ │
│ • 7 Cổng kiểm định tự động         │ │   thương mại điện tử & nhân sự,    │
│ • AI SQL Coach (Socratic Hints)    │ │   truy vấn qua role sqlarena_ai_ro)│
└────────────────────────────────────┘ └────────────────────────────────────┘
```

---

## 2. Tầng Dữ liệu & Khung Năng lực (`enterprise_db` & `sqlarena_app`)

### 2.1. Cơ sở dữ liệu nghiệp vụ thực tế (`enterprise_db`)
Kho dữ liệu thực hành gồm **13 bảng** thuộc lĩnh vực Thương mại điện tử, Chuỗi cung ứng và Nhân sự với hơn **13.400 dòng dữ liệu**:
1. `categories` — Danh mục sản phẩm
2. `suppliers` — Nhà cung cấp
3. `products` — Sản phẩm & giá niêm yết
4. `warehouses` — Kho hàng khu vực
5. `inventory` — Tồn kho theo sản phẩm & kho
6. `customers` — Hồ sơ khách hàng & phân hạng
7. `orders` — Đơn đặt hàng
8. `order_items` — Chi tiết dòng đơn hàng
9. `payments` — Giao dịch thanh toán
10. `shipments` — Vận chuyển & giao nhận
11. `departments` — Phòng ban doanh nghiệp
12. `employees` — Nhân sự & quản lý trực tiếp
13. `reviews` — Đánh giá sản phẩm của khách hàng

Mọi truy vấn từ quá trình AI sinh đề, AI kiểm định, học viên chạy thử (`Sandbox Run`) và chấm điểm (`Submit Grade`) đều kết nối qua role chỉ đọc **`sqlarena_ai_ro`** với giới hạn `statement_timeout = 3000ms` và `TRANSACTION READ ONLY`.

### 2.2. Ba phân vùng Schema ứng dụng (`sqlarena_app`)
- **`core.*`**: Quản lý người dùng (`core.users`), khung thế giới dữ liệu (`core.worlds`), khung 6 kỹ năng (`core.skills`), cấu hình hệ thống (`core.system_settings`) và nhật ký kiểm toán (`core.audit_logs`).
- **`draft.*`**: Lưu trữ các tác vụ sinh đề (`draft.generation_jobs`), bản nháp câu hỏi do Model A sinh (`draft.question_drafts`), lịch sử giải độc lập của Model B (`draft.self_solve_runs`) và nhật ký gọi LLM (`draft.llm_call_logs`).
- **`live.*`**: Ngân hàng câu hỏi chính thức (`live.questions`), bộ kiểm thử (`live.test_cases`), bộ đề tuần (`live.weekly_sets`, `live.weekly_set_items`), bài nộp của học viên (`live.submissions`) và hồ sơ năng lực (`live.user_skill_profiles`).

### 2.3. Khung 6 Kỹ năng SQL (`S1–S6`)
| Mã | Tên kỹ năng | Nội dung trọng tâm |
|---|---|---|
| `S1` | `SELECT / WHERE` | Truy vấn cơ bản, lọc điều kiện, sắp xếp `ORDER BY`, giới hạn `LIMIT` |
| `S2` | `JOIN Multi-Table` | Kết nối nhiều bảng (`INNER JOIN`, `LEFT JOIN`, Self-Join) |
| `S3` | `GROUP BY / HAVING` | Tổng hợp dữ liệu (`COUNT`, `SUM`, `AVG`) và lọc nhóm `HAVING` |
| `S4` | `Subquery / CTE` | Truy vấn con lồng nhau và biểu thức bảng chung (`WITH ... AS`) |
| `S5` | `Window Functions` | Hàm cửa sổ (`ROW_NUMBER`, `RANK`, `DENSE_RANK`, `LAG`, `LEAD`, `SUM() OVER`) |
| `S6` | `Edge Cases & NULL` | Xử lý `NULL` (`COALESCE`, `NULLIF`), `CASE WHEN`, chia cho 0 và trùng lặp |

---

## 3. Quy trình Sinh đề & Kiểm định Kép (Dual-Model AI Pipeline)

Để loại bỏ hiện tượng ảo giác (Hallucination) khi AI tự ra đề và tự viết đáp án sai, hệ thống áp dụng kiến trúc **Hai Mô Hình Độc Lập (Generator – Blind Reviewer)**:

### Bước 1: Thiết kế Blueprint & Sinh đề bởi Model A (`llama3`)
- Khi Quản trị viên tạo Job sinh đề (chọn cấp độ khó, kỹ năng mục tiêu `S1–S6`, số lượng câu và chủ đề nghiệp vụ), **Model A (`llama3`)** đóng vai trò **Generator**.
- Model A nhận lược đồ `enterprise_db`, thiết kế câu hỏi nghiệp vụ bằng tiếng Việt kèm câu lệnh SQL đáp án mẫu (`candidate_sql`).
- Hệ thống thực thi `candidate_sql` trực tiếp trên PostgreSQL 17 (`enterprise_db`) để thu thập bảng kết quả chuẩn (`expected_result`).

### Bước 2: Giải độc lập mù (Blind Self-Solve) bởi Model B (`qwen2.5-coder:7b`)
- **Model B (`qwen2.5-coder:7b`)** chỉ được đọc **đề bài tiếng Việt** và **lược đồ bảng** — tuyệt đối không được nhìn thấy `candidate_sql` của Model A.
- Model B tự viết câu truy vấn SQL độc lập trong tối đa **3 lần thử (`self_solve_runs`)**.
- Mỗi câu SQL của Model B được chạy thật trên `enterprise_db` và so khớp tập kết quả (số dòng, tên cột, giá trị từng ô dữ liệu) với kết quả của Model A.

### Bước 3: Kiểm định qua 7 Cổng chất lượng (7 Verification Gates)
Mỗi bản nháp (`draft.question_drafts`) được chấm qua 7 cổng tự động:
1. **Cổng 1 — AST & Read-Only Safety**: Chỉ cho phép duy nhất 1 câu lệnh `SELECT` / `WITH`, cấm mọi từ khóa DDL/DML (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `GRANT`, `COPY`, `pg_sleep`) và cấm comment SQL (`--`, `/* */`).
2. **Cổng 2 — Thực thi trên PostgreSQL 17**: Câu lệnh SQL của Model A chạy thành công trên `enterprise_db` trong giới hạn thời gian.
3. **Cổng 3 — Tập kết quả không rỗng (Non-Empty Result Set)**: Kết quả trả về phải có ít nhất 1 dòng dữ liệu thực tế (`row_count >= 1`).
4. **Cổng 4 — Cột dữ liệu tường minh**: Cấm `SELECT *` mơ hồ hoặc các cột trùng tên không có định danh (`alias`).
5. **Cổng 5 — Đối chiếu đồng thuận Model B (`Consensus Pass`)**: Kết quả truy vấn độc lập của Model B khớp với kết quả của Model A.
6. **Cổng 6 — Kiểm tra độ khớp Kỹ năng & Độ khó**: Cấu trúc AST của câu SQL phản ánh đúng nhóm kỹ năng (`JOIN`, `GROUP BY`, `CTE`, `Window Function`) đã yêu cầu.
7. **Cổng 7 — Hiệu năng truy vấn (`EXPLAIN` Cost Gate)**: Đảm bảo truy vấn không gây Cartesian Product (Cross Join ngoài ý muốn) hoặc vượt ngưỡng thời gian thực thi.

- Nếu vượt qua toàn bộ các cổng và đạt đồng thuận giữa Model A & Model B, bản nháp đạt trạng thái **`verified`**.
- Nếu có bất kỳ điểm nghi vấn hoặc bất đồng kết quả nào giữa 2 mô hình, bản nháp được chuyển sang trạng thái **`needs_human`** để Quản trị viên kiểm tra, chỉnh sửa và phê duyệt thủ công.

---

## 4. Quy trình Xuất bản, Làm bài & Chấm điểm Tự động

1. **Phê duyệt & Phát hành (`draft` → `live`)**:
   - Khi Quản trị viên bấm **Phê duyệt (Approve)** trên một bản nháp, hệ thống tự động tạo bản ghi trong `live.questions` và đóng gói bộ `live.test_cases` chuẩn.
   - Các câu hỏi trong `live.questions` có thể được gom vào **Bộ đề tuần (`live.weekly_sets`)** để học viên luyện tập và thi đua.
2. **Môi trường Luyện tập & Chấm điểm (`Read-Only Sandbox`)**:
   - Học viên viết truy vấn trên trình soạn thảo Monaco SQL Studio, chạy thử (`Chạy thử SQL`) hoặc nộp bài (`Nộp bài`).
   - Hệ thống kiểm tra an toàn cú pháp trước khi thực thi trên `enterprise_db` dưới quyền `sqlarena_ai_ro`.
   - Bộ chấm điểm so sánh tập kết quả của học viên với từng Test Case chuẩn (kiểm tra thứ tự dòng khi đề có `ORDER BY`, chuẩn hóa số thực và kiểu dữ liệu), cập nhật điểm số vào `live.submissions` và tính toán lại độ thông thạo kỹ năng trong `live.user_skill_profiles`.
