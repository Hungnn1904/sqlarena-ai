# 🇬🇧 Phase 02 — Learner Feedback Bar, Admin Question Bank Resolution UI & Branch Sync  
🇻🇳 *(Giai đoạn 02 — Thanh Bình chọn / Báo lỗi Người học, Giao diện Xử lý tại Ngân hàng đề & Đồng bộ nhánh)*

- 🇬🇧 **Status**: `Completed` (`2026-11-27 17:46`)  
  🇻🇳 *(Trạng thái: Đã hoàn tất lúc `2026-11-27 17:46`.)*

- 🇬🇧 **Evaluator**: `npm run build` + `fe-gate.mjs` + `spec-gate.mjs` + Round-2 `code-reviewer`  
  🇻🇳 *(Bộ kiểm định: `npm run build`, `fe-gate.mjs`, `spec-gate.mjs` và kiểm toán độc lập `code-reviewer`.)*

- 🇬🇧 **Tasks**:  
  🇻🇳 *(Danh sách đầu việc:)*

  - [x] 🇬🇧 Build `frontend/src/components/QuestionFeedbackBar.tsx` (`[ 👍 ] [ 👎 ] [ 🚩 Báo lỗi / Góp ý ]` + 5-reason Modal popup) and embed below the problem statement in `LearnerWorkbench.tsx`.  
    🇻🇳 *(Xây dựng `QuestionFeedbackBar.tsx` gồm thanh nút tinh gọn và hộp thoại báo lỗi 5 nhóm nguyên nhân, nhúng ngay dưới đề bài trong `LearnerWorkbench.tsx`.)*

  - [x] 🇬🇧 Build `frontend/src/components/AdminQuestionFeedbackModal.tsx` and wire `👍/👎`, badge `⚠️ N báo lỗi`, quick filter `Có báo lỗi`, and 3-way resolution (`Thu hồi & Sửa đề`, `Loại bỏ`, `Bỏ qua`) into Tab 5 (`Ngân hàng đề`) of `AdminPortal.tsx`.  
    🇻🇳 *(Xây dựng `AdminQuestionFeedbackModal.tsx` và gắn bộ đếm `👍/👎`, huy hiệu `⚠️ N báo lỗi`, nút lọc nhanh `Có báo lỗi` cùng 3 hướng xử lý trực tiếp vào tab `Ngân hàng đề` trong `AdminPortal.tsx`.)*

  - [x] 🇬🇧 Update `docs/api/OPENAPI_V1.md`, pass independent `code-reviewer` sign-off, push both `origin/main` and `origin/production` to the same verified commit, and run `docker compose down`.  
    🇻🇳 *(Cập nhật tài liệu chuẩn `OPENAPI_V1.md`, vượt qua kiểm toán `code-reviewer`, đồng bộ cả `origin/main` và `origin/production` lên cùng commit mới nhất và tắt Docker.)*

- 🇬🇧 **Done means**: `npm run build`, `fe-gate.mjs`, `spec-gate.mjs`, and `pytest` exit `0`, `origin/main == origin/production`, and `0` `sqlarena-*` containers remain running.  
  🇻🇳 *(Tiêu chí hoàn thành: Tất cả cổng build/test đạt `exit 0`, hai nhánh `origin/main` và `origin/production` trùng khớp commit, và Docker đã tắt sạch.)*

- 🇬🇧 **Verify**: `(cd frontend && npm run build) && node ~/.mykit/skills/fe-anti-slop/scripts/fe-gate.mjs frontend/src --app`  
  🇻🇳 *(Lệnh kiểm chứng: build tĩnh Next.js và chạy `fe-gate.mjs` đạt `0 FAIL`.)*

- 🇬🇧 **Resume From Here**: Start after Phase 01 backend tests pass.  
  🇻🇳 *(Điểm tiếp nối: Bắt đầu ngay khi Phase 01 vượt qua toàn bộ kiểm thử backend.)*
