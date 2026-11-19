# Work Breakdown Structure, Scope & Verification Gates (`docs/WBS.md`)

> Chuẩn hoá theo **MyKit v3.12 (`spec-discovery` + Multi-Senior Debate)**. Mọi giai đoạn gắn chặt với `Owner Agent + SKILL.md + CLI/Script + Exit-0 Gate`.

## 1. Scope Boundary (`Phạm Vi Thực Hiện`)
- **In-Scope (Trong phạm vi):**
  1. **Gom nhóm & Đăng đề hàng loạt (`Question Groups`)**: Ngắt auto-leak ở `promotion.promote()`, tạo bảng `live.question_groups` + `live.question_group_items`, API & giao diện kéo thả / tick chọn nhiều đề (cả từ Drafts lẫn Kho đề `ready`) vào nhóm và đăng toàn bộ nhóm lên kệ trong 1 thao tác (`append_active` hoặc `new_weekly_set`), kèm tự soạn đề thủ công.
  2. **Hiệu chỉnh Kiểm duyệt (`Calibrated Approval`)**: Giữ nguyên chốt chặn uy tín cốt lõi (AST chỉ đọc, chạy thật trên PostgreSQL 17 `row_count > 0`, đồng thuận kết quả giữa các mẫu hợp lệ, bắt buộc `ORDER BY` khi đề yêu cầu, chặn trùng `>= 0.72`), đồng thời gỡ bỏ 8 bẫy bắt bẻ hình thức gây rớt oan (`review.approval_mode = "calibrated"`), khôi phục retry/repair + tăng `max_tokens` trên Gateway, mở duyệt hàng loạt & sửa SQL đáp án cho Admin.
  3. **Kiểm toán & Đại tu UX góc nhìn "Người Mới Chưa Biết Gì"**: Ghi nhật ký ma sát thực tế (`docs/UX_AUDIT_ZERO_KNOWLEDGE.md`), sửa lỗi chữ đen trên nút màu ở Light Mode, khôi phục font `monospace` thật, nâng cỡ chữ `14–16px`, bỏ auto-login ngầm gây hoang mang, lưu nháp SQL theo bài, hiển thị `PK`/`FK` + `output_columns` + trợ lý `AI Coach`/`EXPLAIN`.
  4. **Đóng gói Docker chạy thẳng trên VPS không cần Domain (`http://<VPS_IP>:3000`)**: Nginx `/api/` reverse proxy, sửa `Dockerfile` (`COPY question_create`, non-root user, healthcheck), sửa `postgre/init-docker-db.sh`, ẩn port `5432` nội bộ `127.0.0.1`, thêm `host-gateway` & `scripts/deploy-vps.sh`.
  5. **Nâng cấp chuẩn MyKit v3.12**: Chuẩn hoá `AGENTS.md`, `CLAUDE.md`, `frontend/DESIGN.md`, `docs/{LAW,ARCHITECTURE,WBS,DECISIONS,REVIEW,UX_AUDIT_ZERO_KNOWLEDGE}.md`, `docs/api/OPENAPI_V1.md`.
- **Out-of-Scope (Ngoài phạm vi / Không làm):**
  - Mua tên miền, cấu hình chứng chỉ Let's Encrypt HTTPS hoặc tách hệ thống sang Kubernetes đa cụm (chưa cần thiết khi chạy trực tiếp `http://<VPS_IP>:3000` qua Docker Compose).
  - Thay đổi lược đồ 13 bảng dữ liệu gốc của `enterprise_db` hoặc sửa 50 câu nguồn `ENT-001..ENT-050`.

## 2. Phased Work Breakdown (`Master WBS`)

| ID | Hạng mục bàn giao | Thư mục đích | Owner Agent | Bound Skills (`SKILL.md`) | Gate kiểm chứng (`Exit 0`) | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **WBS-01** | Khung chuẩn MyKit v3.12, Spec, Law, Architecture & Zero-Knowledge UX Audit | `AGENTS.md`, `docs/`, `frontend/DESIGN.md` | `planner` + `speckit-constraint-gatekeeper` | `project-bootstrap`, `spec-discovery`, `fable-idea-rigor` | `spec-gate.mjs .` & `rigor-gate.mjs --self-check` | `[x]` |
| **WBS-02** | Migration `0004_question_groups`, API Gom nhóm/Đăng hàng loạt, Duyệt hàng loạt & Soạn đề tay | `backend/db/`, `backend/alembic/`, `backend/app/` | `backend-architect` | `backend-clean-arch`, `tdd-red-green`, `db-sql-tuning` | `pytest -q` & `backend-gate.mjs .` | `[x]` |
| **WBS-03** | Chế độ kiểm duyệt `calibrated`, chuẩn hoá metadata Model A, sửa comment SQL & BXH tháng | `ai/`, `backend/app/pipeline/`, `backend/app/services/` | `backend-architect` | `tdd-red-green`, `debug-root-cause` | `pytest -q` & `python -m unittest discover` | `[x]` |
| **WBS-04** | Giao diện Kéo thả / Pick Gom nhóm đăng 1 lần + Đại tu UX Người mới & Contrast Light/Dark | `frontend/src/`, `frontend/DESIGN.md` | `frontend-developer` + `ui-finish-gate-reviewer` | `fe-design-system`, `fe-anti-slop` | `npm run build` & `fe-gate.mjs frontend/src --app` | `[x]` |
| **WBS-05** | Docker Compose & Nginx `/api/` Reverse Proxy cho `http://<VPS_IP>:3000` + E2E Live Smoke Test | `Dockerfile`, `docker-compose.yml`, `frontend/nginx.conf`, `scripts/deploy-vps.sh` | `devops-automator` | `devops-deploy`, `verification-gate`, `code-review-eval` | `docker compose up --build -d` + `curl :3000/api/v1/health` + `devops-gate.mjs` | `[x]` |
| **WBS-06** | Đại tu 9 Hạng Mục UX/Grading v2.4: Modal Người dùng, Duyệt đề thuần Admin, Kệ Bộ đề tuần, Lược bỏ AI Coach, Chấm đa Test Case + Tự cuộn, Đồng bộ `ORDER BY` & Scale 80% | `backend/app/`, `ai/`, `frontend/src/`, `docs/plans/261119-2208-ux-grading-overhaul/` | `backend-architect` + `frontend-developer` + `code-reviewer` | `tdd-red-green`, `backend-clean-arch`, `fe-anti-slop`, `verification-gate` | `pytest -q` + `npm run build` + `fe-gate.mjs frontend/src --app` + Live Browser QA | `[x]` |

## 3. Acceptance Criteria (`Tiêu Chí Nghiệm Thu — Done Means`)
- [x] Giảng viên có thể tick chọn hoặc kéo thả nhiều đề đã duyệt (hoặc duyệt hàng loạt từ bản nháp) vào một **Nhóm đề (`Question Group`)**, sắp xếp thứ tự và bấm **Đăng toàn bộ nhóm** 1 lần lên kệ học viên.
- [x] Chế độ kiểm duyệt `calibrated` loại bỏ các lỗi rớt oan hình thức (alias không nêu trong đề, bảng con đủ FK, `2/3` mẫu hợp lệ đồng thuận 100% không mẫu đối kháng, literal trạng thái chuẩn) trong khi giữ vững 100% toàn bộ 48 bài test an toàn/chống gian lận cũ + bộ test TDD mới.
- [x] Giao diện Sáng/Tối đạt tương phản `>= 4.5:1`, không còn chữ đen chìm trên nút màu đậm, cỡ chữ đọc đề `15–16px`, có Onboarding rõ ràng cho người mới, lưu nháp SQL không mất bài, hiện đủ `PK`/`FK` và `output_columns`.
- [x] Toàn bộ stack Docker (`postgres`, `backend`, `worker`, `frontend`) chạy sạch và truy cập qua cổng `:3000` gọi `/api/v1/*` cùng nguồn (same-origin) sẵn sàng cho mọi `http://<VPS_IP>:3000` không cần domain.
- [x] Tất cả cổng kiểm định tự động của MyKit v3.12 đều trả về `exit 0`.

## 4. Verification Commands (`Lệnh Kiểm Chứng Bắt Buộc Exit 0`)
```bash
node "$HOME/.gemini/config/skills/spec-discovery/scripts/spec-gate.mjs" .
node "$HOME/.gemini/config/skills/fable-idea-rigor/scripts/rigor-gate.mjs" --self-check
node "$HOME/.gemini/config/skills/backend-clean-arch/scripts/backend-gate.mjs" .
node "$HOME/.gemini/config/skills/fe-anti-slop/scripts/fe-gate.mjs" frontend/src --app
node "$HOME/.gemini/config/skills/devops-deploy/scripts/devops-gate.mjs"
node "$HOME/.gemini/config/skills/code-review-eval/scripts/eval-check.mjs" .
node "$HOME/.gemini/config/skills/verification-gate/scripts/verification-before-completion-verify.cjs"
```
