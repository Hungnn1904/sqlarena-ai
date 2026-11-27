# 🇬🇧 Approval Brief — Learner Feedback & Branch Synchronization (`SOLO` / Fast-Track)  
🇻🇳 *(Bản tóm tắt phê duyệt — Hệ thống Phản hồi câu hỏi & Đồng bộ nhánh `main`/`production`)*

- 🇬🇧 **Goal**: Implement Human-in-the-Loop learner question voting (`👍`/`👎`) and error reporting (`🚩 Báo lỗi / Góp ý`) with 3-way Admin resolution (`Thu hồi & Sửa đề`, `Loại bỏ / Retire`, `Bỏ qua / Dismiss`) in `Ngân hàng đề`, then synchronize `origin/main` and `origin/production`.  
  🇻🇳 *(Mục tiêu: Xây dựng tính năng bình chọn `👍`/`👎` và `🚩 Báo lỗi / Góp ý` phía Người học kèm 3 hướng xử lý của Quản trị viên tại `Ngân hàng đề`, sau đó đồng bộ hoàn toàn nhánh `origin/main` và `origin/production`.)*

- 🇬🇧 **Critical Safety Invariant**: Never mutate `live.questions.is_flagged` on learner report submission because `weekly.py` and `groups.py` block `is_flagged = true` questions; learner reports strictly aggregate metrics without auto-locking or auto-retiring any question.  
  🇻🇳 *(Bất biến an toàn cốt lõi: Tuyệt đối không bật `live.questions.is_flagged` khi người học gửi báo lỗi vì `weekly.py` và `groups.py` chặn câu hỏi `is_flagged = true`; báo lỗi chỉ tổng hợp số liệu cảnh báo mà không tự động khóa hay gỡ câu hỏi.)*
