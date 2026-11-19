# Phase 02: Admin Users Modal, Pure Manual Review & Weekly Shelf Composer UX

- **Evaluator**: `npm run build` + `fe-gate.mjs` (`frontend-developer`)
- **Verify**: `(cd frontend && npm run build)`

## Tasks & Done Means
- [x] Add `getAdminUserDetail(userId)` to `frontend/src/lib/api.ts` and clickable account rows + User Detail Modal in `AdminPortal.tsx` Tab 1 (`Người dùng`).
- [x] Remove the AI `review.approval_mode` bar from Tab 3 (`Duyệt đề`) so Tab 3 is strictly human verification.
- [x] In Tab 4 (`Bộ đề tuần`) left panel: remove `Tất cả Approved`, keep `Chưa có trên kệ` as default, and add `Đã có trên kệ` tab with total + `Dễ / Trung bình / Khó` breakdown and active shelf list.
- [x] Remove `↑` and `↓` arrow buttons on draft group items in Tab 4 (`Bộ đề tuần`), keeping `Gỡ` and drag-and-drop.
- [x] Filter top group selector bar in `Bộ đề tuần` to `status === 'draft'` only; upon publishing a group, switch away from it so published groups appear solely in `Danh sách Bộ đề tuần` below.
