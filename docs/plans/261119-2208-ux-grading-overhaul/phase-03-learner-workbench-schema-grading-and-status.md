# Phase 03: Learner Workbench Inline Schema, Grading Checkpoints, Auto-Scroll & Status Label

- **Evaluator**: `npm run build` + `fe-gate.mjs` (`frontend-developer`)
- **Verify**: `(cd frontend && npm run build)`

## Tasks & Done Means
- [x] Change wrong-attempt status badge in `LearnerWorkbench.tsx` exercise table from `"Đang thử"` to `"Chưa làm được"`.
- [x] Remove the `"Chèn tên cột vào SELECT"` button inside the required columns panel.
- [x] Move `Sơ đồ bảng dữ liệu` (question's required tables, `PK`/`FK` columns, and `Xem 5 dòng mẫu` button) directly inside the left problem card right beneath the prompt & required columns.
- [x] Remove the `Trợ lý học tập` toolbar (`Gợi ý hướng giải`, `Giải thích lỗi SQL`, `Phân tích hiệu năng (EXPLAIN)`) and remove `coach` / `explain` tabs from the execution console.
- [x] Render explicit `Test case 1: Đúng / Sai`, `Test case 2: Đúng / Sai`, `Test case 3: Đúng / Sai` rows in the submission result notification panel and smoothly `scrollIntoView` to that panel whenever `Nộp bài` finishes.
