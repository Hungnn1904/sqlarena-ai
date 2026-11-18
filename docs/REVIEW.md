# Hồ Sơ Kiểm Chứng Độc Lập & Đối Chiếu 17 Hạng Mục UX/Nghiệp Vụ (`docs/REVIEW.md`)

> Thực thi nguyên tắc **`Hunter != Verifier`** của **MyKit v3.15** trên toàn bộ `backend/`, `ai/`, `frontend/` và cụm `Docker Compose` (`:3000` Học Viên · `:4000` Quản Trị).

## 1. Bảng Kết Quả Các Cổng Kiểm Định Tự Động (`All Must Exit 0`)

| Cổng kiểm chứng | Phạm vi quét | Lệnh thực thi | Kết quả |
| :--- | :--- | :--- | :---: |
| **Spec & Repo Hygiene** | Root + `docs/` | `node ~/.gemini/config/skills/spec-discovery/scripts/spec-gate.mjs . --strict` | `PASS (0 FAIL, 0 WARN)` |
| **Fable Rigor** | Claim typing & Invariants | `node ~/.gemini/config/skills/fable-idea-rigor/scripts/rigor-gate.mjs --self-check` | `PASS` |
| **TDD Discipline** | 12 test suites across repo | `node ~/.gemini/config/skills/tdd-red-green/scripts/test-driven-development-verify.cjs .` | `PASS` |
| **Backend Pytest** | 60 integration tests (PG17 thật) | `(cd backend && ../.venv/bin/pytest -q)` | `PASS (60 passed)` |
| **AI Engine Unittest** | 104 AST & solver tests | `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)` | `PASS (104 tests OK)` |
| **Clean Architecture** | Dependency & modularity | `node ~/.gemini/config/skills/backend-clean-arch/scripts/clean-arch-gate.cjs .` | `PASS (0 errors)` |
| **DB & SQL Safety** | SQL/schema/code files | `node ~/.gemini/config/skills/db-sql-tuning/scripts/db-gate.mjs .` | `PASS (0 FAIL)` |
| **Security OWASP & Vault** | Secrets, BOLA, Read-only | `node ~/.gemini/config/skills/security-owasp-defense/scripts/security-gate.mjs .` | `PASS (0 FAIL, 0 WARN)` |
| **Frontend Static Build** | Next.js 16 (`frontend/dist`) | `(cd frontend && npm run build)` | `PASS` |
| **FE Anti-Slop 4-Linter** | UI/CSS/TSX files | `node ~/.gemini/config/skills/fe-anti-slop/scripts/fe-gate.mjs frontend/src --app` | `PASS (0 FAIL)` |
| **Tech Diagramming SVG** | `docs/diagrams/*.svg` | `python3 -B ~/.gemini/config/skills/tech-diagramming/scripts/generate-from-template.py --self-check` | `PASS` |
| **DevOps & Maskara Scan** | Dockerfiles & Secret scan | `devops-gate.mjs` & `factory-maskara-gate.mjs scan docs` | `PASS (0 findings)` |
| **Completion Gate** | Full workspace asset check | `node ~/.gemini/config/skills/verification-gate/scripts/verification-before-completion-verify.cjs` | `PASS (0 failures)` |

---

## 2. Sổ Đối Chiếu Nghiệm Thu Chi Tiết Giao Diện & Luồng Nghiệp Vụ

| # | Màn hình / Khu vực | Yêu cầu chuẩn hoá | Trạng thái nghiệm thu |
| :---: | :--- | :--- | :---: |
| **1** | **Tách Cổng Web & RBAC (`:3000` & `:4000`)** | Học viên (`role=learner`) trên `:3000` ẩn 100% nút Quản trị; màn chưa đăng nhập chỉ có tiêu đề + Đăng nhập/Đăng ký; Admin (`role=admin`) hiện đúng nhãn `Quản trị viên` và vào được `Quản trị` trên cả `:3000` lẫn `:4000`. | `PASS` |
| **2** | **Làm bài — Tìm kiếm Chính xác & Bảng màu Gốc** | Khôi phục bảng màu Warm Paper `#F5EDDC` & Editorial Sage; gõ `SQL1`/`SQL2` khớp chính xác tuyệt đối vị trí bài (`position`), không lọt `SQL20`/`SQL22` hay ID nội bộ. | `PASS` |
| **3** | **Tiến độ — Lịch sử nộp bài** | Xoá cột `Điểm` (`0/100`), hiển thị rõ 3 trạng thái: `Làm được`, `Không làm được`, hoặc `RTE`; xoá chân trang & badge `N`. | `PASS` |
| **4** | **Bảng Xếp Hạng & Bục Top 3** | Xoá cả cột `Điểm` lẫn `Tốc độ`; xếp Hạng #1 cao nhất ở giữa, Hạng #2 bên trái, Hạng #3 bên phải; đồng bộ 1 tông màu duy nhất. | `PASS` |
| **5** | **Quản trị (`:4000`) — Thứ tự Tab** | Xoá khối 3 thẻ giới thiệu đầu trang; đưa tab **`Người dùng`** lên đầu tiên bên trái và mở mặc định. | `PASS` |
| **6** | **Sinh đề AI — Theo từng Kỹ năng** | Xoá chữ mô tả rườm rà & tên model nội bộ (`ollama`/`llama3`/`qwen`); chọn nhiều kỹ năng `S1–S6` tự tách dòng nhập số lượng câu riêng cho từng kỹ năng (`skill_quantities`). | `PASS` |
| **7** | **Danh sách sinh đề & Log AI** | Đổi thành `Danh sách sinh đề` hiện trực tiếp câu hỏi (topic thu nhỏ), đồng bộ tức thì trạng thái chấm duyệt AI; thu gọn khung Nhật ký gọi AI. | `PASS` |
| **8** | **Duyệt đề (`Approved <-> Needs_Human`)** | Xoá nút `Requeue`; đề `approved` lên thẳng web `:3000`; `needs_human` có `Phê duyệt` & `Từ chối`; `approved` có `Chuyển về Cần duyệt` & `Từ chối` (tự gỡ khỏi `:3000`). | `PASS` |
| **9** | **Bộ đề tuần — Mục `Approved`** | Hiển thị danh sách câu hỏi đang ở trạng thái `Approved` ngay trong tab `Bộ đề tuần`, hỗ trợ chọn/gom nhóm và đăng hàng loạt. | `PASS` |
