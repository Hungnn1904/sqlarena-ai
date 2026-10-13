# SQLArena AI — EnterpriseDB: Quy tắc xây dựng 50 câu SQL nguồn (v1)

**Trạng thái:** Baseline thiết kế để triển khai và kiểm chứng; taxonomy độ khó là **quy ước tạm thời**, sẽ hiệu chỉnh về sau khi nghiên cứu bộ Excel câu hỏi cũ.

## 1. Mục tiêu và ranh giới

- Tạo **đúng 50 câu hỏi SQL nguồn khác nhau về mục tiêu nghiệp vụ/logic truy vấn**, phục vụ phát triển SQLArena AI.
- World là **EnterpriseDB Dataset v1**: 16 bảng, chạy PostgreSQL, sử dụng đúng schema và dữ liệu hiện tại; **không tạo, cập nhật, xóa hay reset dữ liệu**.
- Chỉ sinh bài toán có lời giải **đọc dữ liệu**: `SELECT`, có thể dùng `WITH ... SELECT`, `WITH RECURSIVE`, JOIN, aggregate, subquery, window function, hàm ngày tháng PostgreSQL. **Không** dùng `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `COPY ... TO PROGRAM`, `SELECT INTO`, `CALL`, `DO`, `EXPLAIN ANALYZE` trên SQL không tin cậy, hoặc hàm có tác dụng phụ.
- Đây là **50 câu nguồn để kiểm chứng**, chưa tạo bảng quản lý đề `core/draft/live`, chưa vận hành Model A/Model B, chưa sinh câu cho người dùng cuối.
- Lưu vào JSON trước; không sửa `schema_code.sql`, `constraint.sql`, `enterprise_seed_data.sql`, Generator hay các validator BR.

## 2. Chốt quota độ khó

| Difficulty | Số câu | Tỷ lệ |
|---|---:|---:|
| Easy | 20 | 40% |
| Medium | 20 | 40% |
| Hard | 10 | 20% |
| **Tổng** | **50** | **100%** |

### 2.1. Taxonomy độ khó v1

**Easy:** Mục tiêu đơn bước, ít biến đổi. Thường 1 bảng hoặc JOIN 2 bảng trực tiếp; lọc/sắp xếp/đếm/tổng hợp đơn giản. Không bắt buộc subquery, window, CTE; đầu ra và điều kiện rõ ràng.

**Medium:** Cần phối hợp 2–3 bước suy luận, hoặc nhiều quan hệ; nhóm và lọc nhóm, anti-join/EXISTS, tính tổng hợp theo nhóm, window cơ bản, CTE đơn giản, điều kiện nghiệp vụ phối hợp. Không xếp Medium chỉ vì dùng JOIN hay viết SQL dài.

**Hard:** Cần nhiều tầng biến đổi hoặc reasoning theo chuỗi lịch sử/sự kiện, stock running total có điều kiện, so sánh các giai đoạn, recursive hierarchy, ranking qua nhiều tầng, xử lý edge cases và tie-breaker. Không gắn Hard chỉ vì SQL có CTE/window; cần lập luận tại sao vượt mức Medium.

**Độ khó được đánh giá theo lời giải đơn giản hợp lý nhất**, không theo một reference SQL cố tình làm phức tạp. Nếu blueprint không phù hợp mức đã giao, phải thiết kế lại blueprint **trong quota**, không tự chuyển mức mà làm lệch tổng 20/20/10.

## 3. Quota kỹ năng trọng tâm

Mỗi câu có **đúng 1 `primary_skill_group`**, nhiều `secondary_skills` được phép. Quota nhóm tính theo **primary_skill_group** để không đếm trùng.

| Mã | Kỹ năng trọng tâm | Easy | Medium | Hard | Tổng |
|---|---|---:|---:|---:|---:|
| S1 | SELECT / WHERE / ORDER BY / DISTINCT | 8 | 0 | 0 | 8 |
| S2 | JOIN / LEFT JOIN / SELF JOIN | 7 | 3 | 0 | 10 |
| S3 | GROUP BY / HAVING / aggregate | 5 | 5 | 0 | 10 |
| S4 | Subquery / EXISTS / NOT EXISTS | 0 | 6 | 1 | 7 |
| S5 | CTE / window functions | 0 | 6 | 4 | 10 |
| S6 | Recursive CTE / truy vấn lịch sử & tồn kho đa bước | 0 | 0 | 5 | 5 |
| | **Tổng** | **20** | **20** | **10** | **50** |

**Quy tắc phân loại:**
- S1: lọc/chọn/sắp xếp trực tiếp, không có kỹ năng cao hơn là trọng tâm.
- S2: trọng tâm là nối và hiểu quan hệ; SELF JOIN không tự động là Hard.
- S3: trọng tâm là nhóm/tổng hợp; HAVING có thể Medium.
- S4: trọng tâm là phép tồn tại/không tồn tại hoặc subquery; không bắt buộc dùng đúng cú pháp nếu giải pháp tương đương đơn giản hơn — khi đó cần cân nhắc lại kỹ năng trọng tâm.
- S5: trọng tâm là window/CTE để thực hiện phân tích khác biệt về nghiệp vụ; **CTE chỉ để bọc một SELECT không đủ để nâng độ khó**.
- S6: trọng tâm là bài toán lịch sử, tồn kho tích lũy phức tạp hoặc đệ quy; chỉ tính vào S6 khi cần suy luận nhiều bước thật sự, không vì sử dụng bảng `inventory_transactions`.
- Nếu kỹ năng thực tế của reference SQL lệch blueprint, phải sửa và ghi nhận, không đánh dấu PASS tự động.

## 4. Quota vùng nghiệp vụ chính

Mỗi câu có đúng **1 `primary_business_domain`**, nhưng được phép đọc các bảng ở nhiều domain.

| Domain | Quota |
|---|---:|
| Customer Management | 8 |
| Sales & Orders | 13 |
| Product & Inventory | 12 |
| Human Resources | 9 |
| Finance | 8 |
| **Tổng** | **50** |

Có kiểm soát độ phủ: sử dụng đa dạng các quan hệ của cả 16 bảng trên toàn bộ 50 câu (không bắt buộc mỗi bảng phải là trọng tâm). Nếu bảng nào chưa được sử dụng, ghi rõ nguyên nhân; ưu tiên có ít nhất một câu thực sự khai thác bảng đó khi hợp lý.

## 5. Quy định thiết kế từng câu

Mỗi câu phải có:
- `question_id` ổn định dạng `ENT-001` ... `ENT-050`; `world_id` = `enterprise_v1`.
- `title`, `question_text` bằng tiếng Việt rõ ràng, có bối cảnh hợp lý.
- `difficulty` = `easy|medium|hard`, `difficulty_reason` giải thích bằng 1–3 câu dựa trên taxonomy.
- `primary_skill_group` = `S1` ... `S6`; `secondary_skills` (mảng).
- `primary_business_domain`, `tables_used` đúng schema hiện hành.
- `output_columns` (tên alias + ý nghĩa nếu cần), yêu cầu lọc/nhóm/sắp xếp, quy tắc đồng hạng, NULL, thời gian, đơn vị tiền và giới hạn kết quả nếu liên quan.
- `reference_sql`: một truy vấn PostgreSQL chỉ đọc, chạy được trên EnterpriseDB v1.
- `validation`: trạng thái, số dòng, thời gian chạy, kiểu cột, tóm tắt kết quả, thông báo lỗi nếu có; **không tự điền PASS trước khi chạy thật**.
- `logic_signature`: mô tả chuẩn hóa mục tiêu bài toán + grain của kết quả + phép biến đổi chính, dùng kiểm tra trùng logic.

### 5.1. Đề bài phải giải được từ dữ liệu có sẵn

- Không tạo câu cần cột/bảng chưa tồn tại, không đòi hỏi dữ liệu chưa được lưu, không suy đoán business policy không có trong BR.
- Nếu hỏi doanh thu, nêu rõ đang tính **giá trị đơn hàng**, **tiền thanh toán thành công**, hay **tiền ròng sau refund**; không đánh đồng.
- Nếu hỏi thời gian, chỉ rõ dùng `order_date`, `shipped_at`, `delivered_at`, `attempted_at` hay `transaction_date`.
- Nếu dùng `LIMIT`/Top N, quy định tie policy và sắp xếp ổn định; nếu đầu ra là tập hợp không thứ tự, không dựa vào thứ tự dòng để chấm.
- Không dùng kết quả tự đoán để viết đề; query trả 0 dòng **không tự động FAIL**, nhưng phải có lý do nghiệp vụ và mục đích kiểm tra rõ ràng; tránh quá nhiều câu rỗng/trivial.

### 5.2. Độ đa dạng và tránh trùng lặp

- Không chỉ đổi câu chữ, tên bảng/cột hay tham số để coi là câu mới.
- Tránh hai câu có cùng yêu cầu nghiệp vụ, grain, quan hệ lọc, và hình dạng phép tính dù cách viết khác.
- Phân biệt: đề trùng logic, SQL tương đương hợp lệ, và câu cùng kỹ năng nhưng khác bài toán thật sự.
- Tạo `logic_signature`; so sánh cặp câu theo mục tiêu, bảng trung tâm, cách kết hợp, output grain, phép lọc/aggregation/window, edge case. Đánh dấu cặp nghi ngờ để duyệt thủ công hoặc chỉnh lại.
- Có đủ tình huống có/không có quan hệ, nhiều bản ghi liên quan, NULL hợp lệ, top/tie, thời gian và chuỗi lịch sử, nhưng không yêu cầu thay đổi seed.

## 6. Quy trình thực hiện bắt buộc

### Giai đoạn A — Blueprint

1. Đọc schema PostgreSQL cuối cùng, tài liệu BR và mô tả EnterpriseDB; xác nhận database đọc dữ liệu v1.
2. Sinh đúng 50 blueprints, mỗi blueprint có `question_id`, `difficulty`, `primary_skill_group`, `primary_business_domain`, `tables_used`, `business_goal`, `output_grain`, `expected_output`, `edge_cases`, `logic_signature`.
3. Kiểm tra **cả ba quota**: độ khó, kỹ năng × độ khó, domain.
4. Loại blueprint trùng logic/không khả thi trước khi viết reference SQL.
5. Lưu `question_blueprints.json` và bảng tổng kết phân bố.

### Giai đoạn B — Sinh câu và reference SQL

6. Với từng blueprint, tạo đề hoàn chỉnh, reference SQL, metadata; lưu `questions_candidates.json`.
7. Chỉ dùng đọc dữ liệu. SQL được thực thi bằng tài khoản DB **read-only**, transaction read-only, statement timeout và chỉ trên EnterpriseDB v1 hoặc bản sao cùng dữ liệu.

### Giai đoạn C — Validation

8. Kiểm tra cú pháp, schema và quyền read-only.
9. **Thực thi thật** tất cả reference SQL; ghi row count, runtime, cột kết quả, kết quả mẫu/hash hợp lý. Không ghi thông số bịa đặt.
10. Kiểm tra ngữ nghĩa: đề ↔ reference SQL ↔ kết quả, độ khó thực chất, logic_signature, trùng lặp và chất lượng đầu ra. Nếu có thể, dùng một lời giải độc lập thứ hai cho các câu phức tạp để đối chiếu; không tự coi SQL chạy được là đáp án đúng.
11. Sửa/retry câu sai, **không sửa World/seed**; trường hợp không thể giải bằng world hiện có, thay blueprint mà giữ quota.
12. Chỉ khi thực sự đạt mới đưa vào `questions_validated.json`; câu chưa đạt vào `questions_rejected.json` kèm lý do.
13. Kết thúc với **đúng 50 câu validated**, nếu chưa đủ phải ghi thật số đạt và lý do, không tự khai báo hoàn tất.

## 7. Tiêu chí PASS cho từng câu

- SQL chỉ đọc, chạy được, không timeout trong ngưỡng cấu hình.
- Tham chiếu đúng bảng/cột PostgreSQL thực tế.
- Đề xác định được logic và output; reference SQL thực sự đáp ứng yêu cầu.
- Kết quả ổn định khi chạy lại trên cùng v1; xử lý đồng hạng và thứ tự đầu ra rõ.
- Kết quả có ý nghĩa; zero rows chỉ được chấp nhận khi được chủ đích giải thích.
- Độ khó hợp lý; nhóm kỹ năng phù hợp với logic cần giải.
- Không trùng bài toán với câu đã chấp nhận.
- Tổng cuối cùng đúng 50 câu + đúng quota đã duyệt.

**Phân biệt rõ**: `sql_executed=true` **không đồng nghĩa** `semantic_valid=true`.

## 8. Đầu ra

```text
question_generation/
  difficulty_taxonomy_v1.md
  question_blueprints.json
  questions_candidates.json
  questions_validated.json
  questions_rejected.json
  validation_report.json
  validate_questions.py
  enterprise_source_questions_guide.md
```

Metadata phải có cấu trúc nhất quán, dễ chuyển sau này vào `core.source_questions`. **Không tạo core/draft/live DB ở giai đoạn này.**

## 9. Bất biến và kiểm soát thực thi

- **Không sửa** file `enterprise_seed_data.sql`, `schema_code.sql`, `constraint.sql`, Generator, Validator BR, hay dữ liệu `enterprise_db`.
- Không chạy lệnh `generate_seed.py --validate` hoặc bất kỳ reset/reseed nào.
- Mọi truy vấn đề phải chạy bằng quyền chỉ đọc; dùng cấu hình kết nối ngoài mã nguồn, không hardcode mật khẩu.
- Nếu thiếu quyền/kết nối: tạo artifacts có thể kiểm tra nhưng đánh dấu `NOT_EXECUTED`; không giả báo 50/50 PASS.
- Định nghĩa độ khó và quota **chỉ là baseline v1**: giữ log và phiên bản để sau này so sánh với dữ liệu Excel, không thay đổi âm thầm trong cùng một đợt.
