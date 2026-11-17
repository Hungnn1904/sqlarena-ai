# Hồ Sơ Kiểm Chứng Độc Lập & Kiểm Toán UX Người Mới (`docs/REVIEW.md`)

> Thực thi nguyên tắc **`Hunter != Verifier`** của **MyKit v3.15** trên toàn bộ `backend/`, `ai/`, `frontend/` và cụm `Docker Compose`.

## 1. Bảng Kết Quả Các Cổng Kiểm Định Tự Động (`All Must Exit 0`)

| Cổng kiểm chứng | Phạm vi quét | Lệnh thực thi | Kết quả |
| :--- | :--- | :--- | :---: |
| **Spec & Repo Hygiene** | Root + `docs/` | `node ~/.gemini/config/skills/spec-discovery/scripts/spec-gate.mjs . --strict` | `PASS (0 FAIL, 0 WARN)` |
| **Fable Rigor** | Claim typing & Invariants | `node ~/.gemini/config/skills/fable-idea-rigor/scripts/rigor-gate.mjs --self-check` | `PASS` |
| **TDD Discipline** | 12 test suites across repo | `node ~/.gemini/config/skills/tdd-red-green/scripts/test-driven-development-verify.cjs .` | `PASS` |
| **Backend Pytest** | 56 integration tests (PG17 thật) | `(cd backend && ../.venv/bin/pytest -q)` | `PASS (56 passed)` |
| **AI Engine Unittest** | 104 AST & solver tests | `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)` | `PASS (104 tests OK)` |
| **Clean Architecture** | Dependency & modularity | `node ~/.gemini/config/skills/backend-clean-arch/scripts/clean-arch-gate.cjs .` | `PASS (0 errors)` |
| **DB & SQL Safety** | 90 SQL/schema/code files | `node ~/.gemini/config/skills/db-sql-tuning/scripts/db-gate.mjs .` | `PASS (0 FAIL)` |
| **Security OWASP & Vault** | Secrets, BOLA, Read-only | `node ~/.gemini/config/skills/security-owasp-defense/scripts/security-gate.mjs .` | `PASS (0 FAIL, 0 WARN)` |
| **Frontend Static Build** | Next.js 16 (`frontend/dist`) | `(cd frontend && npm run build)` | `PASS` |
| **FE Anti-Slop 4-Linter** | 39 UI/CSS/TSX files | `node ~/.gemini/config/skills/fe-anti-slop/scripts/fe-gate.mjs frontend/src --app` | `PASS (0 FAIL)` |
| **Tech Diagramming SVG** | `docs/diagrams/*.svg` | `python3 -B ~/.gemini/config/skills/tech-diagramming/scripts/generate-from-template.py --self-check` | `PASS` |
| **DevOps & Maskara Scan** | Dockerfiles & Secret scan | `devops-gate.mjs` & `factory-maskara-gate.mjs scan docs` | `PASS (0 findings)` |
| **Completion Gate** | 341 workspace files | `node ~/.gemini/config/skills/verification-gate/scripts/verification-before-completion-verify.cjs` | `PASS (0 failures)` |

---

## 2. Nhật Ký Kiểm Toán UX Góc Nhìn "Người Mới Chưa Biết Gì" (`Zero-Knowledge Audit`)

Đóng vai sinh viên & giảng viên lần đầu mở ứng dụng trên trình duyệt thực tế (`Zero-Knowledge Live Docker QA`), ghi nhận 8 điểm gây rối mắt/khó tương tác và đối chiếu kết quả sau khi khắc phục:

| # | Trải nghiệm gây vướng trước khi sửa (`OBSERVED`) | Nguyên nhân kỹ thuật gốc | Bản vá đã triển khai & Kiểm chứng trên Docker |
| :---: | :--- | :--- | :--- |
| **1** | Vừa mở trang lần đầu đã tự đăng nhập ngầm vào tài khoản `Bình Nguyên (PTIT)` làm sẵn 8 bài; bấm Đăng xuất rồi F5 lại bị ép vào lại. | `home-client.tsx` gọi `loginUser('nguyen_ptit')` tự động khi trống token. | Thay bằng màn hình chào mừng **Quick-Start Hero** sáng rõ với 3 lựa chọn chủ động (*Sinh viên Demo*, *Giảng viên Demo*, *Tài khoản riêng*). |
| **2** | Ở chế độ Sáng (Light Mode), các nút bấm chính màu xanh đậm / nâu đồng bị hiển thị **chữ màu đen chìm nghỉm** khó đọc. | Luật `html.light .text-white` dùng `!important` đè lên cả nút nền đậm trong `globals.css`. | Tách lớp `.btn-primary`, `data-solid-btn="true"` và badge `.badge-easy/medium/hard` đạt độ tương phản `>= 4.5:1` trên cả Sáng & Tối. |
| **3** | Đang là Sinh viên vẫn thấy tab `Quản trị`, bấm chuông thông báo bị văng sang báo lỗi không có quyền (`403`). | `AuthBar.tsx` hiển thị tab Admin cho mọi role và gọi ngầm `getAdminDrafts()`. | Ẩn hoàn toàn tab `Quản trị` và ngắt polling Admin khi `role !== 'admin'`; gom đổi vai trò chấm bài vào menu **Chế độ Demo** gọn ở góc phải. |
| **4** | Đề bài chữ bé li ti (`12px`), danh sách bài có gần 20 nút lọc rối mắt và xếp câu AI khó lên trước bài cơ bản. | Dùng `text-xs` tràn lan, mặc định `newest_ai_first`. | Nâng đề bài lên **`16px` (`leading-relaxed`)**, font `monospace` chuẩn (`tabular-nums`), mặc định xếp **Dễ → Khó**, thu gọn bộ lọc nâng cao. |
| **5** | Tập viết `JOIN` nhưng nhìn cột Schema không biết khóa chính/khóa ngoại; nộp đúng logic vẫn báo Sai do đoán lệch tên cột; chuyển bài mất code đang gõ. | UI bỏ sót `pk`/`references`, API thiếu `output_columns`, đổi bài ghi đè `setSql()`, cấm `-- comment`. | Hiển thị nhãn **`PK`** & **`FK -> bảng.cột`**, thanh **`output_columns`** kèm nút chèn nhanh vào `SELECT`, tự lưu nháp vào `localStorage`, cho phép `-- comment` và gắn nút **`AI Coach` / `EXPLAIN`**. |
| **6** | Giảng viên phải bấm duyệt từng câu một, không sửa trực tiếp được SQL đáp án, không gom đề vào nhóm để đăng cùng lúc được. | Thiếu API & UI gom nhóm hàng loạt, `weekly_sets` chỉ hiện 2 ô nhập chữ. | Dựng trung tâm **4 Bước Ra Đề**: Duyệt hàng loạt (`bulk-approve`), sửa `custom_sql`, soạn đề tay, và bảng **2 cột Kéo thả / Tick chọn vào Nhóm đề -> Đăng toàn bộ 1 lần**. |
