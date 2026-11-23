# Approval Brief — Pipeline Stepper & 5-Block Acceptance Dossier (`261123-1611`)
*(Tóm tắt phê duyệt — Thanh tiến trình sinh đề & Hồ sơ nghiệm thu 5 khối)*

- **Purpose**: `commercial` (PTIT Capstone observability & technical acceptance proof on `main` only; `production` locked at `d733787`).
  *(Mục đích: `commercial` — bổ sung minh chứng nghiệm thu kỹ thuật trên nhánh `main`; giữ nguyên nhánh `production` tại `d733787`.)*
- **Invariants**: Zero extra LLM calls; zero leaked local model names (`qwen`/`llama`/`deepseek`/`ollama`); zero conversational example copy hardcoded into UI.
  *(Bất biến kỹ thuật: Không phát sinh thêm lượt gọi LLM; không lộ tên model nội bộ; không gán cứng câu chữ ví dụ minh họa vào UI.)*
- **Verify**: `(cd backend && ../.venv/bin/pytest -q)` + `(cd frontend && npm run build)`
  *(Lệnh kiểm chứng: chạy trọn bộ `pytest` backend và `npm run build` frontend.)*
