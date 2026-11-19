# Plan: Unassigned Approved Pool & Clean Neutral UI Copy (`261120-0019`)

## Context & Goal
1. **Unassigned Approved Pool Law**: Newly approved drafts (both AI-approved in `Sinh đề AI` and Admin-approved in `Duyệt đề`) must enter `live.questions (status='ready')` + `live.test_cases` in the **Unassigned Approved Pool** (`Câu hỏi Approved chưa có trên kệ` in `Bộ đề tuần`) and **must never** auto-insert into `live.weekly_set_items` (`Làm bài` shelf) until an Admin explicitly publishes them via a Question Group or Weekly Set.
2. **Zero Unrequested Mode Toggles / Conversational Examples in UI**: Remove the `AI duyệt: Thông minh | Khắt khe` toggle and state from `AdminPortal.tsx`, filter internal `review.approval_mode` out of the `Cấu hình` table, neutralize `settings_registry.py` description, and scrub conversational user examples (`SQL tuần 6`, `Ví dụ: ...`, `VD: ...`) from UI copy.

## Phases
- [x] **Phase 01 — Backend Unassigned Promotion & Neutral Settings (`phase-01-backend-unassigned-approval.md`)** (`2026-11-20 00:24`)
- [x] **Phase 02 — Frontend Removal of Approval Mode Toggle & Clean Copy (`phase-02-frontend-clean-copy.md`)** (`2026-11-20 00:25`)

## Resume From Here
- Active Phase: Completed (`2026-11-20 00:25` — all gates green).
