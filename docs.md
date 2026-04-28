# SQLArena AI — Technical Handoff Notes

## 1. Mục đích file này

Handoff tổng hợp để nắm nhanh toàn bộ context dự án:

- Nguồn gốc hệ thống và bức tranh lớn
- Scope thật của repo hiện tại
- Kiến trúc và pipeline chi tiết
- Stack + trạng thái implementation thực tế
- Gap giữa vision và repo hiện tại
- Những điểm cần phát triển tiếp

---

## 2. Ba lớp cần phân biệt rõ

| Layer | Tài liệu | Trạng thái |
|---|---|---|
| **Learn SQL** | PDF gốc | Đã chạy thật tại PTIT, 800+ sinh viên, 30.000+ submit |
| **SQLArena** | DOCX vision | Bản mở rộng lớn — thiết kế sản phẩm, chưa chắc đã full implement |
| **sqlarena-ai repo** | Repo này | Prototype cho subsystem AI question generation |

> Đừng đọc DOCX rồi tưởng toàn bộ platform đã tồn tại trong code.

---

## 3. Bức tranh lớn

### 3.1. Learn SQL (nền móng đã chạy thật)

- Hệ thống chấm SQL tự động, triển khai thực tế tại PTIT
- Kiến trúc microservice: Spring Boot, Kafka, Eureka, Gateway
- Multi-DB: PostgreSQL, MySQL, SQL Server
- Chấm bằng **execution** — chạy SQL thật, so sánh output thật
- Sandbox isolation: prefix bảng ngẫu nhiên, giới hạn quyền, timeout, row limit, cleanup

### 3.2. SQLArena (vision sản phẩm)

Mở rộng Learn SQL thành platform đầy đủ:

- Học SQL theo lộ trình + AI sinh đề + AI feedback
- Battle Royale realtime
- Social Feed, Achievement, Cosmetic
- Multi-tenant cho trường học và doanh nghiệp
- Enterprise API cho tuyển dụng / đào tạo
- NoSQL support (MongoDB)
- Chứng chỉ tùy biến theo tổ chức

### 3.3. Repo này (prototype AI question generation)

Implement phần nhỏ trong SQLArena: pipeline tự động sinh câu hỏi SQL bằng LLM.

---

## 4. Triết lý kỹ thuật cốt lõi

### Chấm bằng execution, không đoán

Thay vì "đọc SQL rồi đoán đúng sai", hệ thống:

1. Tạo DB sandbox
2. Nạp schema + seed data
3. Chạy SQL người dùng submit
4. So sánh output với đáp án chuẩn

Ưu điểm: khách quan, chấp nhận nhiều cách viết đúng.

### AI chỉ làm phần phù hợp với AI

- **Deterministic** cho grading (execution engine)
- **AI** cho generation, explanation, adaptation

---

## 5. Pipeline 7 bước (thiết kế gốc từ pipeline.html)

### Bước 1 — Skill Taxonomy DB

Xây "từ điển kiến thức": topic SQL, mức độ khó, lỗi phổ biến, few-shot seed, pattern câu tốt. Không cho LLM sáng tác tự do từ số 0.

### Bước 2 — Skill Target Selector

Chọn topic cần sinh dựa trên: pass rate, avg attempts, hint usage, avg time, config admin. Phân biệt "topic khó" vs "câu hỏi mơ hồ" vs "người học thiếu concept".

### Bước 3 — Question Planner

LLM tạo blueprint trước: intent, target_skill, schema hint, trap_strategy, ambiguity risk. Ép AI lên kế hoạch trước → giảm token lãng phí, phát hiện vấn đề sớm.

### Bước 4 — Question Generator

LLM sinh đầy đủ: `schema_sql`, `seed_sql`, `question_text`, `answer_sql`, `expected_output`.

### Bước 5 — Clarity Check

Hai lớp: linguistic clarity (câu có mơ hồ không) + ground truth assertion (rule-based). Không phụ thuộc hoàn toàn vào AI tự kiểm tra AI.

### Bước 6 — Execution Engine Verify

Chạy đáp án thật trên DB sandbox. Kiểm tra: cú pháp, runtime, output, FK consistency. Đây là "cửa chặn cứng" đáng tin nhất.

### Bước 7 — Output + Metadata + Retry Policy

Đóng gói vào question bank. Retry escalation 3 cấp, archive fallback để đảm bảo SLA (thiết kế gốc: ~100 câu/tuần).

---

## 6. Trạng thái implementation hiện tại

### Đã implement (và hoạt động)

| Component | File | Ghi chú |
|---|---|---|
| Taxonomy | `taxonomy.py` | 12 topics, đủ cấp độ |
| Target selector | `pipeline.py` step2 | Dựa trên stats từ question bank |
| Question planner | `question_planner.py` | Sinh blueprint qua LLM |
| Question generator | `pipeline.py` step4 | Retry logic đã fix |
| Clarity check | `clarity_checker.py` | Score-based, đã calibrate |
| Execution verify | `execution_engine.py` | SQLite sandbox thật |
| Question bank | `question_bank.py` | SQLite, pending_review flow |
| LLM gateway | `llm_gateway.py` | Ollama + Gemini, rate limit handling |
| Retry policy | `retry_policy.py` | 3 attempts + archive fallback |
| FastAPI endpoint | `main.py` | POST /generate |

### Stack thực tế đang chạy

```
AI_PROVIDER : ollama
MODEL       : qwen2.5-coder:3b
DB          : SQLite (questions.db)
Validation  : SQLite sandbox (execution_engine.py)
API         : FastAPI + uvicorn
```

### Chưa có

- Auth / multi-tenant
- Judge service đa DB (MySQL, PostgreSQL, SQL Server)
- Analytics-driven target selection (hiện dùng stats đơn giản)
- AI feedback engine
- Battle Royale / Social / Achievement
- Review queue UI thực sự
- Enterprise API

---

## 7. Gap đã biết và đã fix

| Gap cũ | Trạng thái |
|---|---|
| `llama3` JSON failing liên tục | ✅ Fix — đổi sang `qwen2.5-coder:3b` |
| Retry prompt dùng chuỗi rỗng `""` | ✅ Fix — `build_base_prompt()` tách ra ngoài |
| `num_ctx=4096` output truncate | ✅ Fix — tăng lên `8192` |
| Step3 không catch exception, crash pipeline | ✅ Fix — wrap try/except |
| Clarity check false positive | ✅ Fix — mở rộng action words, threshold 0.5 |
| `google-generativeai` deprecated | ✅ Fix — migrate sang `google-genai` |
| Gemini 2.5 Flash rate limit 5 req/phút | ✅ Documented — dùng 2.0-flash hoặc INTER_QUESTION_DELAY |

Xem `Conclusion.md` để đọc đầy đủ quá trình debug và các hướng đã thử.

---

## 8. Gap còn lại nếu muốn phát triển tiếp

### Nếu chỉ tập trung AI pipeline

- Thêm execution-based validation sâu hơn (FK consistency, DDL handling)
- Thêm domain rotation (đổi theme dữ liệu mỗi tuần)
- Review queue UI để admin approve/reject câu hỏi
- Batch generation ổn định (hiện mỗi run chỉ sinh 3 câu)
- Structured metadata cho từng câu (hints, explanation, tags)

### Nếu tiến tới product lớn hơn

- Tách execution engine thành service riêng hỗ trợ multi-DB
- Kết nối với Learn SQL backend hiện có
- Xác định service boundaries rõ ràng
- Auth + tenant isolation

---

## 9. Thuật ngữ quan trọng

| Thuật ngữ | Giải nghĩa |
|---|---|
| **Execution engine** | Chạy SQL thật rồi lấy output thật để chấm |
| **Sandbox** | Môi trường cô lập, chạy SQL an toàn |
| **DML** | SELECT, INSERT, UPDATE, DELETE |
| **DDL** | CREATE, ALTER, DROP, TRUNCATE |
| **Blueprint** | Kế hoạch câu hỏi LLM lên trước khi sinh đề thật |
| **Taxonomy** | "Từ điển kiến thức" SQL dùng để guide LLM |
| **Seed SQL** | Dữ liệu mẫu nạp vào sandbox để test answer |
| **Pending review** | Trạng thái câu hỏi đã validate kỹ thuật, chờ admin duyệt |
| **Archive fallback** | Pool câu cũ đã verify, dùng khi generation fail hết retry |
| **Multi-tenant** | Một platform phục vụ nhiều tổ chức, dữ liệu tách biệt |
| **LLM** | Mô hình ngôn ngữ lớn (llama3, qwen, gemini...) |

---

## 10. Tóm tắt thực dụng

Nếu cần làm việc với repo này ngay:

- Xem repo như **PoC cho AI question generation** — không phải full platform
- Dùng `DOCX` làm product vision tham chiếu
- Dùng `PDF` làm nền móng kỹ thuật đã proven
- Dùng `pipeline.html` làm target design cho subsystem này
- **Stack hoạt động ngay:** `ollama + qwen2.5-coder:3b`, không cần GPU cao cấp