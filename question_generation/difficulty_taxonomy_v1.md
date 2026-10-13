# EnterpriseDB: taxonomy độ khó v1

Nguồn quy tắc: `../question_create/enterprise_50_question_rules_v1.md`.
Đây là baseline v1, chưa phải độ khó được đo trên người học hay hiệu chỉnh theo bộ Excel.
Đánh giá theo lời giải đơn giản hợp lý nhất, không theo độ dài SQL.

| Mức | Định nghĩa | Số câu |
|---|---|---:|
| Easy | Một bước lọc, tra cứu quan hệ trực tiếp hoặc tổng hợp đơn giản. | 20 |
| Medium | Hai đến ba bước, lọc nhóm, tồn tại/tương quan, vai trò quan hệ phối hợp hoặc window cơ bản. | 20 |
| Hard | Nhiều tầng grain, lượng hóa lồng, đoạn lịch sử, tích lũy có điều kiện hoặc cây đệ quy có xử lý biên. | 10 |

| Kỹ năng chính | Easy | Medium | Hard | Tổng |
|---|---:|---:|---:|---:|
| S1: SELECT / WHERE / ORDER BY / DISTINCT | 8 | 0 | 0 | 8 |
| S2: JOIN / LEFT JOIN / SELF JOIN | 7 | 3 | 0 | 10 |
| S3: GROUP BY / HAVING / aggregate | 5 | 5 | 0 | 10 |
| S4: Subquery / EXISTS / NOT EXISTS | 0 | 6 | 1 | 7 |
| S5: CTE / window | 0 | 6 | 4 | 10 |
| S6: Recursive / lịch sử / tồn kho nhiều bước | 0 | 0 | 5 | 5 |
| Tổng | 20 | 20 | 10 | 50 |

| Nghiệp vụ chính | Số câu |
|---|---:|
| Customer Management | 8 |
| Sales & Orders | 13 |
| Product & Inventory | 12 |
| Human Resources | 9 |
| Finance | 8 |

Mỗi câu có đúng một kỹ năng chính và một nghiệp vụ chính. Bảng đọc và kỹ năng phụ không được cộng vào quota lần nữa.

Phân biệt các trường hợp dễ nhầm trong bộ này:

- ENT-013 chỉ SELF JOIN quản lý trực tiếp, là Easy/S2; ENT-047 duyệt hậu duệ nhiều cấp và tổng hợp cây, là Hard/S6.
- ENT-018 tổng biến động theo loại giao dịch là Easy/S3 dù đọc inventory_transactions. ENT-028 tổng tồn hiện tại và sức chứa là Medium/S3. ENT-046 cần tồn trước kỳ, tích lũy từng tháng, ngưỡng tồn và chuỗi liên tiếp nên là Hard/S6.
- ENT-033 kiểm tra mọi sản phẩm đều active là Medium/S4. ENT-041 cần mọi hàng active đã được giao và tại mọi kho đã giao hàng đó đều còn tồn dương, là Hard/S4 với lượng hóa hai tầng và chống tập rỗng.
- ENT-037 so lương với một mốc trước là Medium/S5. ENT-050 tìm đoạn tăng tối đa, giữ mốc tiền nhiệm và chọn đoạn tăng tổng tốt nhất, là Hard/S6.
- ENT-039 cộng tiền success lũy kế là Medium/S5. ENT-043 hợp nhất tiền vào/ra theo hai ngày sự kiện, lấp lịch tháng, chỉ xét cửa sổ đủ ba tháng và chọn top, là Hard/S5.
- ENT-045 xếp hạng sản phẩm trong nhân viên-quý rồi nhân viên trong quý, cần giữ tổng của mọi sản phẩm; là Hard/S5 vì có hai grain lựa chọn khác nhau.

`difficulty_reason` ở từng câu ghi lập luận riêng. Kết quả SQL và oracle khớp là bằng chứng ngữ nghĩa, không tự chứng minh độ khó sư phạm.
Lịch sử thay đổi thiết kế được ghi trong `validation_report.json`; không âm thầm đổi quota hoặc phiên bản.
