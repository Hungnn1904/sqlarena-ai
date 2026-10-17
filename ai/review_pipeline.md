# SQLArena Review Pipeline v1.3

## Mục tiêu và nguyên tắc

`ai/review.py` kiểm duyệt các draft `pending` bằng PostgreSQL read-only sandbox, nhiều mẫu Model B, kiểm tra AST/rule, đối chiếu kết quả, semantic auditor và tối đa hai vòng sinh lại khi lỗi có thể sửa. Khi được duyệt, pipeline lưu reference SQL và test case vào `draft.test_cases`.

Nguyên tắc quyết định:

- `approved` chỉ khi mọi bước bắt buộc đều qua.
- `needs_human` nếu thiếu bằng chứng, các mẫu bất đồng, contract không khớp, auditor không chắc chắn hoặc không sửa được.
- Không có lời giải hợp lệ là lỗi của lần giải, không tự động chứng minh câu hỏi sai. Mặc định `REVIEW_ZERO_VALID_ACTION=needs_human`.
- Semantic auditor là một lớp phòng vệ bằng LLM, không phải chứng minh hình thức SQL đúng.

## Những thay đổi ở v1.3

1. Tạo `query_contract` khi review từ câu hỏi, `output_columns`, `logic_signature`, output grain, edge cases và quy tắc sắp xếp hiện có. Câu hỏi là nguồn sự thật; metadata chỉ hỗ trợ cấu trúc. Không thêm cột database và không cần migration.
2. Sửa việc đọc `logic_signature.output_grain`.
3. Sửa nhận diện câu không cần sắp xếp, ví dụ `Sắp xếp: Một dòng nên không có yêu cầu thứ tự`; câu này không bắt buộc `ORDER BY`, kể cả khi metadata cũ ghi sai.
4. So sánh `ORDER BY` dựa trên các khóa và chiều được yêu cầu; chấp nhận thêm khóa tie-breaker sau tiền tố bắt buộc. Nếu đề nêu `NULLS FIRST/LAST`, vị trí NULL cũng được kiểm tra.
5. Thêm rule kiểm tra một số hợp đồng diễn đạt rõ ràng trong câu hỏi: loại NULL, ngưỡng aggregate có điều kiện, kiểu DATE của cột tháng, và làm tròn từng chỉ tiêu giờ.
6. Thêm kiểm tra rủi ro JOIN một-nhiều làm nhân bản kết quả khi metadata khai báo grain là một thực thể. Nếu `central_table` vắng mặt, guard có thể suy luận bảng cha từ alias của các cột outer SELECT và quan hệ FK child->parent hiện có. Nếu truy vấn JOIN trực tiếp child table nhưng đầu ra vẫn ở grain parent mà không có DISTINCT/GROUP BY phù hợp, chuyển sang needs_human. Đây là guard thận trọng, không phải chứng minh rằng mọi JOIN như vậy đều sai.
7. Semantic audit nhận contract có cấu trúc và phải có đủ năm nhóm kiểm tra với nhãn riêng biệt: cột đầu ra; điều kiện/aggregate; JOIN/grain/subquery; NULL/ngày/tháng/làm tròn/đơn vị; sắp xếp/tie-breaker. Một nhãn lặp lại hoặc chung chung không được tính cho nhiều nhóm.
8. Có tối đa hai vòng sửa. Mỗi vòng sinh lại `k` lời giải rồi chạy lại toàn bộ guard, thực thi, consensus, contract và auditor. Không dùng reference SQL của tập calibration để làm feedback cho Model B.

## Cài đặt

Không cần database migration cho v1.3.

1. Sao lưu `ai/review.py`, `ai/test_review.py`, `ai/.env.example`, `ai/review_pipeline.md`.
2. Ghi đè các file tương ứng từ gói v1.3.
3. Giữ nguyên `ai/.env` riêng của máy; không chép đè file đó từ `.env.example`.
4. Trong `ai/.env`, đặt tối thiểu:

```dotenv
REVIEW_ZERO_VALID_ACTION=needs_human
REVIEW_SEMANTIC_AUDIT=true
REVIEW_MODEL_NAME=qwen2.5-coder:7b
REVIEW_AUDIT_MODEL_NAME=llama3:latest
REVIEW_AUDIT_NUM_PREDICT=600
REVIEW_REPAIR_ROUNDS=2
```

Đảm bảo cả hai model được cài trong Ollama. Kiểm tra bằng `ollama list`. Không cần tải model lớn hơn để dùng các rule v1.3.

## Kiểm tra theo thứ tự

Chạy tại thư mục gốc `D:\sqlarena-ai`.

### 1. Kiểm tra cú pháp

```powershell
python -m py_compile ai/review.py ai/test_review.py
```

### 2. Chạy unit tests

```powershell
python -m unittest discover -s ai -p "test_review.py" -v
```

Nếu thiếu package, cài dependency dự án bằng:

```powershell
python -m pip install -r requirements.txt
```

### 3. Kiểm tra môi trường PostgreSQL/Ollama

```powershell
python ai/review.py --check
ollama list
```

### 4. Chạy calibration

Giữ nguyên lệnh đang dùng:

```powershell
python ai/review.py --calibrate --skip 15 --limit 20 --samples 3
```

Lệnh vẫn tương thích. Với `REVIEW_REPAIR_ROUNDS=2`, các câu bị chặn vì lý do có thể sửa có thể sinh lại tối đa hai vòng; calibration sẽ lâu hơn và gọi LLM nhiều hơn. Đặt `REVIEW_REPAIR_ROUNDS=0` trong `.env` để đo chỉ một lượt, nhưng không phải khuyến nghị cho lần xác nhận release.

## Đọc kết quả

Mở file JSON mới được in ở cuối lệnh trong `ai/outputs/calibration_*.json`. Kiểm tra:

- `review_version` phải là `review_v1.3.1_contract_audit_repair`.
- `semantic_contract.issues` nêu rule cứng làm câu bị chặn.
- `semantic_audit` chứa verdict, issues và checks của LLM.
- `stages.repair` ghi số vòng thử, lý do ban đầu và có duyệt được sau sửa hay không.
- `approved_WRONG` là lỗi chặn phát hành. Không bật duyệt tự động hàng loạt nếu còn trường hợp đó.
- `needs_human_but_all_samples_correct` gợi ý rule/audit đang chặn một lời giải chạy khớp đáp án; cần xem từng lý do, không nới lỏng toàn bộ fail-closed.

Trước đây, tài liệu này ưu tiên rà ENT-020, ENT-024, ENT-027, ENT-031, ENT-032 và ENT-033. Calibration thực tế mới nhất được cung cấp ngày 2026-10-17 đã ghi nhận `approved_WRONG = 1` ở ENT-017 (3 lời giải đều sai nhưng verdict vẫn `pass`), `approved_correct = 10`, `needs_human = 8`, và `needs_human_but_all_samples_correct = 1`. Vì vậy **không dùng kết quả này để tuyên bố Model B đã an toàn**; ENT-017 là lỗi chặn phát hành cho chế độ duyệt tự động. Xem `test_report.md` để biết giới hạn của bằng chứng hiện có.

## Giới hạn cần hiểu rõ

- Calibration chỉ so với reference SQL trên các dataset được cấu hình. Một dataset không đủ để chứng minh lời giải tổng quát; cấu hình `REVIEW_VARIANT_DBS` để kiểm tra dataset cùng schema khác dữ liệu.
- LLM có thể sinh cùng một lỗi nhiều lần hoặc auditor có thể đánh giá sai. Nhiều mẫu/khác model làm tăng bằng chứng nhưng không bảo đảm đúng.
- Rule theo văn bản chỉ chặn các điều kiện mà nó nhận diện rõ ràng. Những yêu cầu diễn đạt khác hoặc metadata thiếu vẫn có thể cần người kiểm tra.
- Vòng repair sinh lại toàn bộ `k` mẫu; nó không bỏ qua hard rule và không duyệt chỉ vì auditor nói `pass`.
- Calibration gần nhất có `approved_WRONG` ở ENT-017. Phải điều tra và sửa trước khi coi pipeline đủ an toàn để duyệt tự động.
- Không có `approved_WRONG` trong một tập 20 câu sau khi sửa cũng không chứng minh tỷ lệ lỗi thực tế bằng 0. Cần tập holdout không dùng để chỉnh rule và dataset biến thể trước khi phát hành.

## Khuyến nghị khi đổi model

Đổi model không yêu cầu migration database. Tải model bằng `ollama pull <tag>` rồi cập nhật `MODEL_NAME`, `REVIEW_MODEL_NAME` hoặc `REVIEW_AUDIT_MODEL_NAME` trong file `ai/.env` cục bộ. Xác nhận tag bằng `ollama list`, chạy `python ai/review.py --check`, rồi chạy calibration trên cùng tập và cùng `--samples` để so sánh. Chỉ đổi một vai trò mỗi lần để biết thay đổi nào tạo khác biệt. Không sửa `.env.example` như cách cấu hình máy cá nhân, và không commit `ai/.env`.

Không chỉ đo tỷ lệ `approved_correct`: bắt buộc theo dõi `approved_WRONG` (false acceptance), `needs_human_but_all_samples_correct` (false rejection/overblocking), thời gian chạy, số lỗi không giải được và hiệu quả trên tập holdout. Khi còn `approved_WRONG`, không bật duyệt hàng loạt.
