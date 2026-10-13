# TASK — Build, seed, and validate EnterpriseDB end-to-end

Bạn là Senior PostgreSQL Database Engineer + Synthetic Data Engineer. Hãy THỰC THI toàn bộ quy trình, không chỉ viết kế hoạch.

## Files đầu vào
- `schema_code.sql`: nguồn chuẩn xác định DDL và cấu trúc cuối sau migrations.
- `constraint.sql`: constraints/index bổ sung; chạy sau schema.
- `rang_buoc.docx`: BR01–BR16; đọc đầy đủ và đối chiếu với DDL.
- `Schema database(1).docx`: mô tả nghiệp vụ để hiểu ngữ cảnh; một số cột/trạng thái trong tài liệu có thể cũ. Khi khác nhau, schema sau migration và BR đã chốt được ưu tiên; ghi lại mâu thuẫn.
- `validate_enterprisedb_br01_br16.sql`: SQL Validator khởi đầu. Đọc, audit, chạy, và sửa nếu phát hiện thiếu sót; KHÔNG chỉnh validator chỉ để che lỗi dữ liệu.

## Mục tiêu
Tạo một dataset EnterpriseDB thực sự được INSERT vào PostgreSQL, nhất quán 16 BR, đủ đa dạng để sau đó tạo 50 câu SQL (20 Easy, 20 Medium, 10 Hard), mở rộng được 100+. Chưa cần sinh 50 đề SQL trong task này.

## Thực hiện
1. Kiểm tra môi trường PostgreSQL và quyền truy cập. KHÔNG động đến production hoặc database không được phép xóa. Nếu không có thông tin kết nối, hỏi đúng thông tin cần thiết; không tự báo đã chạy thành công.
2. Audit schema, migrations, constraint SQL. Đặc biệt sửa thứ tự migration salary_history: drop constraint `chk_salary_history_amounts` trước khi drop `old_salary`. Kiểm tra trùng tên constraints, trạng thái cột sau migrations, và các CHECK/INDEX mới. Tạo script sửa riêng hoặc bản DDL chạy được từ đầu, không tự ý thay đổi BR.
3. Dùng một database thử nghiệm riêng, tạo schema sạch theo thứ tự `schema_code.sql` (đã sửa) rồi `constraint.sql` (đã kiểm tra). Ghi rõ database được dùng.
4. Thiết kế `data_scenarios.md` và `scenarios.json`: quy mô ~300 customers, 250 products, 100 employees, 8 warehouses, 1000 orders, ~2500 order_items, cùng các bảng còn lại theo tỷ lệ hợp lý. Tạo scenario có chủ đích: khách không có đơn, sản phẩm chưa bán, đa dạng trạng thái đơn, payment failed→success, hoàn tiền một phần/toàn bộ, trả hàng vật lý toàn bộ, hàng tồn bằng 0 và khác 0, cây quản lý nhiều cấp, lịch sử lương, dữ liệu nhiều tháng. Bảo đảm trường hợp biên, NULL hợp lệ, giá trị bằng nhau, nhóm không có bản ghi con; mọi scenario phải tuân BR.
5. Viết Python Generator tái tạo được bằng fixed random seed, sinh dữ liệu theo dependency graph, không tạo dữ liệu ngẫu nhiên độc lập giữa các bảng. Ghi log số lượng từng bảng và scenario; có cách chạy lại an toàn trên database test. Không hard-code kết quả validator.
6. THỰC SỰ chạy generator để INSERT dữ liệu vào PostgreSQL thử nghiệm. Không chỉ xuất CSV hay SQL rồi dừng. Nếu muốn, đồng thời xuất seed SQL/CSV để tái lập.
7. Chạy `validate_enterprisedb_br01_br16.sql` trong cùng một SQL session (vì có TEMP TABLE). Tất cả 16 BR phải PASS, tổng vi phạm = 0. Nếu FAIL: lấy chi tiết, sửa Generator hoặc vấn đề schema/validator thực sự, reset database test và chạy lại. Không tự bỏ bớt BR, không sửa SQL để bỏ qua các dòng sai.
8. Tạo `validate_scenario_coverage.sql` và chạy thật. Báo cáo counts theo bảng, trạng thái, nhóm scenario, và những truy vấn có khả năng trả 0 dòng. Yêu cầu coverage đạt ngưỡng đã thiết kế.
9. Tạo báo cáo `validation_report.md`: môi trường và lệnh chạy, schema version, random seed, số dòng 16 bảng, PASS/FAIL từng BR, coverage từng scenario, các lỗi đã sửa, vấn đề còn mở. Đính kèm log thực thi thật. Phân biệt rõ kết quả đã chạy với kết quả dự kiến.

## Các quy tắc cần giữ
- BR03: trạng thái `pending → processing → shipped → delivered`; hủy từ pending/processing; history bắt đầu pending, chuỗi liên tục, trạng thái cuối khớp orders.
- BR05/06: tồn từng sản phẩm/kho không âm và tổng kho không vượt capacity tại MỌI bước giao dịch theo thời gian.
- BR07: mỗi order dùng tối đa một warehouse; shipped/delivered có đúng một sale cho từng order_item, đúng sản phẩm/kho/số lượng; pending/cancelled không có sale; processing có thể xuất một phần; physical return chỉ sau delivered và trả toàn bộ order, không trả một phần. Monetary refunds độc lập với physical returns.
- BR10: không có cycle manager; manager khác department có thể hợp lệ theo quyết định đã thống nhất. Không tự áp đặt cùng phòng ban.
- BR11: salary_history dùng cột `salary`, không dùng `old_salary/new_salary`; nhân viên có thể không có salary_history.
- BR12: payment chỉ `success`/`failed`; mỗi payment amount = order.total_amount, tối đa 1 success/order, processing/shipped/delivered phải có đúng 1 success; không dùng `payments.completed_at`.
- BR14: chỉ refund `completed` được cộng vào tổng hoàn thành công.
- BR15: dùng `payments.attempted_at`, `refunds.requested_at`, `refunds.completed_at`.
- Không tự ý thêm bảng/cột hoặc chính sách nghiệp vụ mới. Nếu có xung đột tài liệu, ghi nhận và hỏi trước khi đổi ý nghĩa BR.

## Những điểm cần kiểm tra thêm trong validator
- Kiểm tra dữ liệu NULL, số lượng bản ghi con tối thiểu, trạng thái refund có tương ứng completed_at không (nếu chính sách đã xác nhận), trùng thứ tự timestamp và thứ tự transaction_id.
- Kiểm tra consistency giữa status history và shipped_at/delivered_at; đừng coi một check riêng lẻ là đủ cho toàn BR.
- Kiểm tra kịch bản cancelled sau successful payment: tài liệu chưa quy định chính xác hoàn tiền bao nhiêu và khi nào; hỏi nếu scenario này được đưa vào. Tránh scenario đó nếu chưa được xác nhận.
- Không ép một warehouse cho pending order nếu không cần; không gán sale cho cancelled.

## Đầu ra bắt buộc
- `data_scenarios.md`
- `scenarios.json`
- `generate_seed.py` và dependencies/config nếu cần
- `validate_enterprisedb_br01_br16.sql` (bản đã audit nếu thay đổi)
- `validate_scenario_coverage.sql`
- `validation_report.md`
- `README_run.md` ghi các lệnh thực tế để dựng lại toàn bộ từ database test trống
- Dataset đã được nạp vào PostgreSQL thử nghiệm, không chỉ là file

Tiêu chí hoàn thành: database thử nghiệm chứa dữ liệu thật; tất cả BR PASS (0 violations); coverage PASS; các file và hướng dẫn tái tạo được; có bằng chứng chạy thật. Nếu thiếu kết nối hoặc môi trường thực thi, dừng và yêu cầu quyền truy cập thay vì tuyên bố hoàn thành.
