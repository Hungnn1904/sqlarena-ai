# 🇬🇧 Phase 02 — Bottom Independent `Thảo luận (N)` Card & Branch Sync  
🇻🇳 *(Giai đoạn 02 — Khối Card Độc lập `Thảo luận (N)` Cuối Trang & Đồng bộ Nhánh)*

- 🇬🇧 **Status**: `Completed` (`2026-11-27 20:32`)  
  🇻🇳 *(Trạng thái: Đã hoàn tất lúc `2026-11-27 20:32`.)*

- 🇬🇧 **Evaluator**: `npm run build` + `fe-gate.mjs` + `spec-gate.mjs` + `code-reviewer`  
  🇻🇳 *(Bộ kiểm định: `npm run build`, `fe-gate.mjs`, `spec-gate.mjs` và kiểm toán độc lập `code-reviewer`.)*

- 🇬🇧 **Tasks**:  
  🇻🇳 *(Danh sách đầu việc:)*

  - [x] 🇬🇧 Build `frontend/src/components/QuestionDiscussionCard.tsx` (`<390` LOC) with 1-level replies, automatic reputation badges (`Đã giải đúng`, `Đã thử làm`, `Quản trị viên`), soft-locked composer (`"Nộp bài ít nhất 1 lần để tham gia thảo luận"`), and owner/admin delete button, mounted at the very bottom of `LearnerWorkbench.tsx`.  
    🇻🇳 *(Xây dựng `QuestionDiscussionCard.tsx` dưới 390 dòng đặt hẳn dưới cùng trang `LearnerWorkbench.tsx`, hỗ trợ trả lời 1 cấp, huy hiệu uy tín, khóa nhẹ ô nhập khi chưa nộp bài và nút xóa cho chủ bình luận/admin.)*

  - [x] 🇬🇧 Update `docs/api/OPENAPI_V1.md`, pass independent `code-reviewer` audit, push synchronized `origin/main` and `origin/production`, and run `docker compose down`.  
    🇻🇳 *(Cập nhật `OPENAPI_V1.md`, vượt qua kiểm toán `code-reviewer`, đồng bộ cả `origin/main` và `origin/production` và tắt Docker.)*

- 🇬🇧 **Verify**: `(cd frontend && npm run build) && node ~/.mykit/skills/fe-anti-slop/scripts/fe-gate.mjs frontend/src --app`  
  🇻🇳 *(Lệnh kiểm chứng: build tĩnh Next.js và chạy `fe-gate.mjs` đạt `0 FAIL`.)*

- 🇬🇧 **Resume From Here**: Start right after Phase 01 `pytest` suite turns green.  
  🇻🇳 *(Điểm tiếp nối: Bắt đầu ngay sau khi bộ test Phase 01 chạy xanh.)*
