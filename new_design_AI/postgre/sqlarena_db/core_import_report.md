# Báo cáo nhập SQLArena Core v2

Trạng thái: **PASS**.

Thời điểm: `2026-10-10T16:51:50.477413+00:00`.

Nguồn chuẩn: `question_generation/questions_validated.json`; Rules v2 đọc từ `sqlarena_create`.
Không thực thi Reference SQL trong giai đoạn import. PASS trong validation được giữ nguyên từ JSON nguồn.

| Bảng | Số dòng thực tế |
|---|---:|
| core.worlds | 1 |
| core.skills | 6 |
| core.templates | 0 |
| core.source_questions | 50 |

| Kiểm chứng đối chiếu | Số câu khớp |
|---|---:|
| question_text, byte UTF-8 | 50/50 |
| reference_sql, byte UTF-8 | 50/50 |
| validation JSONB | 50/50 |
| metadata còn lại JSONB | 50/50 |
| Tái dựng toàn bộ object nguồn | 50/50 |

Quota từ database:

| Độ khó | Số câu |
|---|---:|
| easy | 20 |
| medium | 20 |
| hard | 10 |

| Kỹ năng | Số câu |
|---|---:|
| S1 | 8 |
| S2 | 10 |
| S3 | 10 |
| S4 | 7 |
| S5 | 10 |
| S6 | 5 |

| Nghiệp vụ | Số câu |
|---|---:|
| Customer Management | 8 |
| Sales & Orders | 13 |
| Product & Inventory | 12 |
| Human Resources | 9 |
| Finance | 8 |

FK orphan: `{'question_skill_orphans': 0, 'question_world_orphans': 0, 'template_world_orphans': 0}`; tất cả bằng 0.
Ma trận kỹ năng theo độ khó cũng được đối chiếu với dữ liệu nguồn.

DDL chạy lại giữ nguyên Core: **True**.
Nhập lại bị chặn trước INSERT và giữ nguyên Core: **True**.
Bộ kiểm tra schema từ chối kỳ vọng cấu trúc khác và giữ nguyên Core: **True**.

Nguồn EnterpriseDB có `16` bảng; FK thật: `24`.
BR trích đủ 01-16 từ tài liệu và đối chiếu đoạn validator: `16`.
Đề xuất và caveat trong tài liệu BR được giữ rõ nguồn, không tự nâng thành chính sách bắt buộc.
`depth=NULL`: chưa quy ước generation depth; không dùng độ sâu SQL hay độ khó làm depth.
`created_at` là thời điểm nhập do PostgreSQL now(), không phải thời điểm sinh câu.

Dữ liệu enterprise_db trước/sau khớp: **True**.
Catalog enterprise_db trước/sau khớp: **True**.
JSON nguồn, generator, seed, schema/constraints/validator và tài liệu trước/sau khớp: **True**.
Không tạo draft/live, không tạo template giả, không lưu mật khẩu, không có bước reset.

Dấu vân tay và log thực thi đầy đủ ở `sqlarena_create/evidence/`.
