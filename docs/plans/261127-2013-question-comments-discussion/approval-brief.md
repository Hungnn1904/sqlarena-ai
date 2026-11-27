# 🇬🇧 Approval Brief — Per-Question SQL Discussion (`SOLO` / Fast-Track)  
🇻🇳 *(Bản tóm tắt phê duyệt — Tính năng Thảo luận / Bình luận theo từng bài SQL)*

- 🇬🇧 **Goal**: Implement `live.question_comments` (`GET`/`POST`/`DELETE /api/v1/questions/{id}/comments*`) and an independent bottom-of-page `Thảo luận (N)` card on `/` supporting 1-level replies, automatic reputation badges (`Đã giải đúng` / `Đã thử làm` / `Quản trị viên`), submission-gated posting (with admin bypass), and owner/admin deletion, synchronized to both `origin/main` and `origin/production`.  
  🇻🇳 *(Mục tiêu: Xây dựng bảng `live.question_comments`, bộ 3 API thảo luận và khối Card độc lập `Thảo luận (N)` ở cuối trang Làm bài hỗ trợ trả lời 1 cấp, gắn nhãn uy tín tự động, khóa nhẹ khi chưa nộp bài trừ admin, xóa bình luận cho chủ sở hữu/admin, và đồng bộ cả `origin/main` lẫn `origin/production`.)*
