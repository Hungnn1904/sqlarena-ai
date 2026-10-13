# Hướng Dẫn Bộ 50 Câu SQL Nguồn EnterpriseDB

Bộ câu hỏi đọc database `enterprise_db` hiện có. Điểm vào để rà soát là
`questions_validated.json` và `validation_report.json`; kết quả phải lấy từ báo cáo lần chạy thực tế.

## Các file

| File | Nội dung |
|---|---|
| difficulty_taxonomy_v1.md | Baseline độ khó và cả ba quota |
| question_blueprints.json | 50 thiết kế, mục tiêu, grain, biên và logic_signature |
| blueprint_distribution.json | Quota của Blueprint |
| questions_candidates.json | 50 đề tiếng Việt và Reference SQL, validation ban đầu NOT_EXECUTED |
| questions_validated.json | Chỉ các câu đã thực thi và đạt kiểm chứng thực tế |
| questions_rejected.json | Các câu chưa đạt cùng lỗi; mảng rỗng khi mọi câu đạt |
| validation_report.json | Bằng chứng mỗi câu, thời gian, kiểu cột, mẫu, hash, quota và bất biến |
| validate_questions.py | Script kiểm chứng, chỉ đọc DB |
| db_readonly.py | Kết nối psql, giới hạn câu SELECT và role chỉ đọc |
| semantic_oracles.py | Phép tính Python độc lập cho cả 50 câu |
| question_specs.py | Nguồn thiết kế và Reference SQL, không kết nối DB |
| build_questions.py | Xuất Blueprint trước rồi candidate; không kết nối DB |
| schema_snapshot.json | Cột, constraints, foreign keys và indexes thực tế đã đọc |
| logic_duplicate_review.json | So sánh 1.225 cặp và ghi nhận các họ câu gần nhau |
| execution_history.json | Tóm tắt các lượt kiểm chứng đã lưu và phiên bản candidate |

## Chạy kiểm chứng lại

Yêu cầu Python, `psql` và kết nối được đến database hiện có. Không cần cài package Python.
Script tìm `psql` trong PATH hoặc `C:/Program Files/PostgreSQL/*/bin/psql.exe`;
có thể chỉ rõ `PSQL_BIN`.

Từ thư mục gốc workspace, dùng PowerShell:

```powershell
$env:PGHOST = 'localhost'
$env:PGPORT = '5432'
$env:PGDATABASE = 'enterprise_db'
$env:PGUSER = 'postgres'
$questionDbSecret = Read-Host 'Mat khau PostgreSQL' -AsSecureString
$env:PGPASSWORD = [System.Net.NetworkCredential]::new('', $questionDbSecret).Password
try {
    python -B .\question_generation\validate_questions.py --timeout-ms 15000
} finally {
    Remove-Item Env:\PGPASSWORD
}
```

Mật khẩu không nằm trong mã nguồn, JSON hoặc báo cáo. Cũng có thể dùng `pgpass.conf` thay biến môi trường.
Database bị giới hạn tên `enterprise_db`; script không tạo database, role, schema hay dữ liệu.

Tài khoản đăng nhập được cung cấp là postgres. Trước mọi SELECT, script dùng
`SET LOCAL ROLE pg_read_all_data` để chạy với role có sẵn chỉ đọc,
`BEGIN ... READ ONLY`, search_path `pg_catalog,public`, timezone UTC và statement timeout.
Báo cáo kiểm tra role thực tế không là superuser, không có quyền CREATE trong public,
có SELECT và không có quyền ghi trên cả 16 bảng. Không tạo tài khoản mới.
Nếu không chuyển được role hoặc không kết nối được, câu hỏi được ghi NOT_EXECUTED và script trả exit code khác 0.

Nếu chỉnh thiết kế, xuất lại theo hai bước:

```powershell
python -B .\question_generation\build_questions.py --blueprints-only
python -B .\question_generation\build_questions.py
```

Sau đó phải chạy kiểm chứng lại; candidate mới không tự được PASS.

## Cách kiểm chứng

1. Đọc Rules, schema/constraints/BR và xác nhận schema sau migration, gồm salary_history.salary và inventory_transactions.order_item_id. payments không có completed_at.
2. Kiểm tra quota, ID, signature và SQL trùng; so sánh các họ câu tương tự theo mục tiêu, quan hệ, grain, biến đổi và biên. Review thiết kế do Agent thực hiện, không tuyên bố đã được người dùng duyệt.
3. Đọc snapshot của 16 bảng trong một transaction REPEATABLE READ READ ONLY và catalog thực tế. Không import snapshot vào database khác.
4. Với từng Reference SQL, kiểm tra từ vựng SELECT được phép, dùng PostgreSQL gdesc để xác nhận cú pháp/kiểu cột, EXPLAIN JSON không ANALYZE để đối chiếu bảng thật, rồi thực thi câu SELECT trong một lớp JSON để thu toàn bộ kết quả.
5. So toàn bộ giá trị, NULL và thứ tự với oracle Python độc lập tính từ các dòng bảng gốc. Ví dụ ENT-048 dùng quét từng ngày, khác cách cắt khoảng hiệu lực trong Reference SQL.
6. Thực thi Reference SQL lần hai và so hash/thứ tự. Chỉ chuyển PASS khi SQL thực thi, ngữ nghĩa khớp và kết quả ổn định.
7. Đọc lại dữ liệu/catalog và so SHA-256 trước/sau; so hash các file seed, generator, schema, constraints và validator cũ. Kiểm tra lại quota trên các câu PASS.

`runtime_ms` là thời gian statement PostgreSQL từ psql timing, có tính lớp đóng gói JSON.
`process_wall_ms` còn tính thời gian khởi động psql và truyền kết quả.
NUMERIC trong kết quả mẫu được lưu thành chuỗi thập phân để tránh mất chính xác;
`column_types` giữ kiểu PostgreSQL thực tế. Hash chuẩn hóa giữ NULL, boolean, thứ tự dòng và giá trị số chính xác.

Mỗi đề quy định tiền là giá trị đơn, giá trị dòng hàng, payment success, tiền ròng hoặc chỉ số lập ngân sách.
Ngày ghi nhận và quy tắc đồng hạng nằm trong đề, không phụ thuộc ngày chạy hiện tại.
Các tham số phân tích như ngưỡng tồn 50 không được gọi là Business Rule.

Không chạy validator BR cũ trong giai đoạn này vì nó tạo/ghi bảng tạm; tài liệu và log BR từ giai đoạn trước là nguồn tham chiếu.
Việc nhận diện v1 đối chiếu số dòng với seed_summary hiện có và ghi fingerprint của dữ liệu đang đọc;
không tuyên bố có fingerprint lịch sử nguyên bản từ thời điểm seed.
Hash trước/sau phát hiện thay đổi ròng trong khoảng kiểm chứng; kết quả oracle hoặc hash khác làm câu/bộ kiểm chứng không đạt.
Độ khó là baseline thiết kế v1, chưa phải đánh giá từ người học. Không tạo core/draft/live ở giai đoạn này.
