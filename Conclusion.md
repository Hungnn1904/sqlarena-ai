# Conclusion — SQLArena AI Pipeline: Before vs After

## 1. Bối cảnh

Pipeline `pipeline.py` có nhiệm vụ tự động sinh câu hỏi SQL theo 3 mức độ (easy / medium / hard) thông qua LLM, validate kết quả, rồi lưu vào question bank.

**Phiên bản gốc** khi nhận được: chạy với `ollama + llama3`, kết quả `generated=0, valid=0, failed=3`.  
**Phiên bản hiện tại**: chạy với `ollama + qwen2.5-coder:3b`, kết quả `generated=3, valid=3, failed=0, valid_rate=1.0`.

---

## 2. Danh sách vấn đề được phát hiện

### Vấn đề 1 — LLM trả về JSON không hợp lệ (nguyên nhân gốc rễ)

**Triệu chứng:**
```
WARNING: LLM did not return valid JSON: Expecting ',' delimiter: line 6 column 150
WARNING: LLM JSON missing keys: {'question_text', 'answer_sql', 'seed_sql', 'schema_sql'}
WARNING: 'list' object has no attribute 'keys'
```

**Nguyên nhân:** `llama3` (8B) không đủ khả năng instruction-following để sinh JSON dài và phức tạp một cách ổn định. Model thường trả về JSON bị truncate, thiếu key, hoặc trả về plain text/SQL thay vì JSON object.

---

### Vấn đề 2 — `num_ctx=4096` quá nhỏ, output bị cắt giữa chừng

**Triệu chứng:** JSON bị truncate trước khi đóng ngoặc, dẫn đến parse error.

**Nguyên nhân:** Prompt generator nhúng toàn bộ DDL schema + seed SQL + few-shot example + blueprint. Tổng input dễ vượt 2000 token, khiến output bị cắt khi context window chỉ có 4096.

---

### Vấn đề 3 — Retry logic dùng prompt rỗng

**Triệu chứng:** Attempt 2, 3 vẫn fail tương tự attempt 1 dù đã có retry prompt modifier.

**Nguyên nhân:** `base_prompt` được build bên trong `step4_generate_question()`, không accessible ở `_generate_one()`. Khi step4 fail, `last_prompt` bị reset về `None`. Lần retry tiếp theo gọi `get_retry_prompt("", attempt, ...)` — truyền chuỗi rỗng, khiến model nhận prompt không có schema, không có blueprint, tất nhiên tiếp tục fail.

```python
# Lỗi cũ
override = get_retry_prompt(last_prompt or "", attempt, ...)  # last_prompt luôn là ""
```

---

### Vấn đề 4 — Clarity check quá strict, false positive

**Triệu chứng:**
```
WARNING: Clarity failed attempt=1 issues=['Missing action word (expected one of: find, list, show, ...)']
```

**Nguyên nhân:** `is_clear = len(issues) == 0` — bất kỳ 1 issue nào cũng reject câu hỏi. Action word list quá hẹp, thiếu các từ LLM hay dùng như `what`, `which`, `who`, `write`, `provide`. Câu hỏi hoàn toàn hợp lệ về mặt SQL bị loại chỉ vì phrasing khác convention.

---

### Vấn đề 5 — Step3 không được catch, crash toàn pipeline khi API lỗi

**Triệu chứng:**
```
ValueError: No JSON object found in LLM output
Traceback (most recent call last): ... pipeline.py line 287
```

**Nguyên nhân:** `step3_plan_question()` được gọi trực tiếp trong `_generate_one()` mà không có try/except. Khi API lỗi (429, 503) hoặc LLM trả về output không parse được ở bước planning, exception không được catch → crash toàn bộ pipeline thay vì gracefully skip và tiếp tục.

---

### Vấn đề 6 — `google-generativeai` deprecated (phát sinh khi thử Gemini)

**Triệu chứng:**
```
FutureWarning: All support for the google.generativeai package has ended.
```

**Nguyên nhân:** Package `google-generativeai` đã bị Google ngừng hỗ trợ, cần migrate sang `google-genai`.

---

### Vấn đề 7 — Gemini model name sai và API version không khớp

**Triệu chứng:**
```
404 NOT_FOUND: models/gemini-2.5-flash-preview-04-17 is not found for API version v1beta
```

**Nguyên nhân 1:** `.env` set `MODEL_NAME=gemini-2.5-Flash` nhưng code chỉ đọc `GEMINI_MODEL` → fallback về `gemini-2.0-flash` âm thầm.  
**Nguyên nhân 2:** `gemini-2.5-flash` chỉ available trên `v1alpha`, không có trên `v1beta` mà `google-genai` dùng mặc định.  
**Nguyên nhân 3:** Tên preview (`gemini-2.5-flash-preview-04-17`) đã bị Google retire, không còn tồn tại.

---

### Vấn đề 8 — Gemini free tier rate limit 429 (phát sinh khi thử Gemini)

**Triệu chứng:**
```
429 RESOURCE_EXHAUSTED: Quota exceeded, limit: 5 requests/minute for gemini-2.5-flash
```

**Nguyên nhân:** Free tier `gemini-2.5-flash` chỉ cho 5 req/phút. Pipeline gọi liên tiếp không có delay → vượt quota ngay từ câu thứ 2. Retry logic dùng `time.sleep(2 ** attempt)` — quá ngắn so với thời gian reset quota (25-31s).

---

## 3. Câu hỏi cần được trả lời (cần chỉnh)

| # | Câu hỏi | Trạng thái |
|---|---------|-----------|
| 1 | Model nào đủ khả năng sinh JSON ổn định mà chạy được trên máy local? | ✅ Đã trả lời |
| 2 | Retry logic có đang hoạt động đúng không? | ✅ Đã trả lời |
| 3 | Clarity check có đang reject câu hỏi hợp lệ không? | ✅ Đã trả lời |
| 4 | Dùng Gemini hay Ollama? | ✅ Đã quyết định |
| 5 | Máy GTX 1650 4GB VRAM chạy được model nào? | ✅ Đã trả lời |
| 6 | Docker có giúp chạy model lớn hơn không? | ✅ Đã trả lời (không) |

---

## 4. Các hướng giải quyết đã thử

### 4.1. Giữ `llama3`, tăng `num_ctx` lên 8192
- **Kết quả:** Không thực hiện riêng — được gộp vào fix chung `llm_gateway.py`
- **Nhận xét:** Cần thiết nhưng không đủ. `llama3` vẫn yếu về JSON following dù context lớn hơn

### 4.2. Chuyển sang Gemini 2.5 Flash (free tier)
- **Kết quả:** ❌ Không thành công hoàn toàn
- **Lý do thất bại:**
  - API key bị Google auto-revoke sau khi lộ public
  - Model name `gemini-2.5-Flash` → cần normalize
  - Preview version `04-17` đã bị retire → đổi sang `05-20` → vẫn 404
  - `google-generativeai` deprecated → migrate sang `google-genai`
  - API version `v1beta` không support `gemini-2.5-flash` → cần `v1alpha`
  - Sau khi vượt qua tất cả trên: free tier chỉ 5 req/phút → 429 liên tục từ câu thứ 2
- **Bài học:** `gemini-2.5-flash` free tier không phù hợp cho pipeline batch nhiều câu liên tiếp

### 4.3. Gemini 2.0 Flash thay thế (đề xuất nhưng không thực hiện)
- **Lý do không thử:** Người dùng quyết định chuyển về Ollama
- **Nhận xét:** 2.0 Flash có 15 req/phút trên free tier, thực tế hơn cho usecase này

### 4.4. Chuyển sang `qwen2.5-coder:3b` trên Ollama
- **Kết quả:** ✅ Thành công
- **Lý do chọn:** Fit vừa 4GB VRAM của GTX 1650, chuyên code/SQL, JSON following tốt hơn llama3
- **Kết quả thực tế:** `generated=3, valid=3, failed=0, valid_rate=1.0`

### 4.5. Docker
- **Kết quả:** ❌ Không giải quyết được vấn đề
- **Lý do:** Docker chạy trên cùng hardware, không thay đổi GPU/CPU/RAM available. Bottleneck là phần cứng, không phải môi trường

---

## 5. Chi tiết các thay đổi code

### `pipeline.py`
| Thay đổi | Lý do |
|----------|-------|
| Tách `build_base_prompt()` thành hàm độc lập | Expose base_prompt ra ngoài `step4` để retry có thể dùng |
| `_generate_one`: build `base_prompt` trước vòng loop, pass vào `get_retry_prompt()` | Fix retry logic dùng prompt rỗng |
| Wrap `step3_plan_question()` trong try/except | Tránh crash toàn pipeline khi API lỗi ở bước planning |
| Thêm `INTER_QUESTION_DELAY` giữa các câu hỏi | Buffer cho rate limit (chủ yếu cho Gemini) |

### `llm_gateway.py`
| Thay đổi | Lý do |
|----------|-------|
| `num_ctx: 4096 → 8192` | Tránh output bị truncate |
| Đọc `MODEL_NAME` làm fallback cho `GEMINI_MODEL` | `.env` dùng `MODEL_NAME`, code chỉ đọc `GEMINI_MODEL` |
| Migrate `google-generativeai` → `google-genai` | Package cũ deprecated |
| Thêm `_GEMINI_MODEL_ALIASES` normalize tên model | Tránh case-sensitive mismatch |
| Set `api_version="v1alpha"` cho `gemini-2.5-*` | 2.5 Flash không có trên v1beta |
| Parse `retryDelay` từ 429 response, sleep đúng thời gian | Retry sau đúng thời gian Google yêu cầu thay vì 2^n giây |
| Phân biệt 429 vs 503 trong backoff | 429 cần sleep dài (~30s), 503 chỉ cần 10s |

### `clarity_checker.py`
| Thay đổi | Lý do |
|----------|-------|
| Mở rộng `_ACTION_WORDS` thêm `what`, `which`, `who`, `write`, `provide`... | LLM hay phrasing khác convention, bị reject oan |
| `is_clear = score >= 0.5` thay vì `len(issues) == 0` | Cho phép 1 issue nhỏ, chỉ reject khi thực sự mơ hồ |

### `requirements.txt`
| Thay đổi | Lý do |
|----------|-------|
| `google-generativeai` → `google-genai` | Package cũ deprecated |

---

## 6. Kết luận

Pipeline đã đi từ **0% success rate** lên **100% success rate** sau một loạt fix tầng tầng lớp lớp. Vấn đề không phải do một lỗi duy nhất mà là sự chồng chất của nhiều lỗi nhỏ: model yếu, context window nhỏ, retry logic broken, clarity check quá strict, và API integration sai.

**Nguyên nhân gốc rễ thực sự** là chọn sai model ban đầu (`llama3`). Mọi fix khác chỉ là vá víu xung quanh — khi đổi sang `qwen2.5-coder:3b` thì phần lớn vấn đề JSON tự biến mất.

**Điểm còn hạn chế:**
- `qwen2.5-coder:3b` vẫn là model nhỏ, chất lượng câu hỏi sinh ra chưa phải tốt nhất
- Pipeline hiện chỉ sinh 1 câu/difficulty mỗi lần chạy, chưa batch lớn
- Toàn bộ câu hỏi ở trạng thái `pending_review` — chưa có review flow thực sự

**Stack cuối cùng hoạt động:**
```
AI_PROVIDER=ollama
MODEL_NAME=qwen2.5-coder:3b
OLLAMA_HOST=http://localhost:11434
```