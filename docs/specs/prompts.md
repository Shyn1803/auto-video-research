# Prompt Specification

**Version:** 1.0 · Seed vào bảng `prompts` / `prompt_versions` (FR-14) khi khởi tạo DB
Template engine: Jinja2. Mỗi prompt có: name, biến bắt buộc, tier LLM, tiêu chí đánh giá output. Output có cấu trúc dùng **JSON mode / structured output** với Pydantic schema tương ứng — retry 2 lần nếu parse fail, lần 3 → task fail.

Nguyên tắc chung cho mọi prompt:
- Ngôn ngữ output: **tiếng Việt** (trừ tên riêng, thuật ngữ kỹ thuật giữ nguyên).
- Cấm bịa: mọi thông tin phải truy được về source được cung cấp trong context; không có nguồn → ghi "chưa xác minh".
- Số liệu giữ nguyên đơn vị gốc, kèm nguồn `[source_id]`.

---

## 1. `research.summarize` — tier `cheap`

Biến: `topic`, `article_title`, `article_content`, `source_url`

```
Bạn là trợ lý nghiên cứu công nghệ AI. Tóm tắt bài viết sau bằng tiếng Việt,
phục vụ việc sản xuất video ngắn về chủ đề "{{ topic }}".

Bài viết: {{ article_title }} ({{ source_url }})
---
{{ article_content }}
---
Yêu cầu output JSON:
{
  "summary_vi": "3-5 câu tóm tắt, tập trung thông tin MỚI và SỐ LIỆU cụ thể",
  "key_facts": ["mỗi fact 1 câu, có số liệu/tên/ngày cụ thể nếu bài nêu"],
  "relevance_to_topic": 0-10,
  "published_info": {"date": "YYYY-MM-DD hoặc null", "author": "hoặc null"}
}
Chỉ dùng thông tin CÓ TRONG bài viết. Không suy diễn.
```

Đánh giá: summary không chứa thông tin ngoài bài; key_facts ≤ 6; relevance chấm đúng bài lạc đề (spot check 10 bài/tuần đầu).

## 2. `ranking.score` — tier `cheap`

Biến: `topic`, `sources_json` (list {id, title, summary_vi, published_at, provider, trusted})

```
Chấm điểm các nguồn tin sau cho video về "{{ topic }}". Hôm nay: {{ today }}.
Tiêu chí (trọng số): Độ mới ({{ w_recency }}), Liên quan ({{ w_relevance }}),
Tin cậy ({{ w_trust }} — nguồn trusted/paper/blog chính thức cao hơn),
Được xác nhận chéo ({{ w_confirm }} — nhiều nguồn nói cùng một việc).

{{ sources_json }}

Output JSON: {"rankings": [{"source_id": "...", "score": 0-100, "reason_vi": "1 câu"}]}
```

## 3. `factcheck.extract_claims` — tier `strong`

Biến: `script_or_summary`, `topic`

```
Trích xuất mọi CLAIM KIỂM CHỨNG ĐƯỢC từ nội dung sau (tên model, số benchmark,
ngày phát hành, tên paper, repo github, số phiên bản, so sánh định lượng).
Bỏ qua ý kiến chủ quan.

{{ script_or_summary }}

Output JSON: {"claims": [{"claim_text": "nguyên văn ngắn gọn",
  "claim_type": "model_name|benchmark|release_date|paper|github|version|other"}]}
```

## 4. `factcheck.verify_claim` — tier `strong`

Biến: `claim_text`, `evidence_json` (đoạn trích từ các source chứa từ khoá liên quan)

```
Kiểm chứng claim sau dựa DUY NHẤT trên các trích đoạn nguồn cung cấp.

CLAIM: {{ claim_text }}
NGUỒN: {{ evidence_json }}   // [{source_id, quote, source_trusted}]

Output JSON: {
  "verdict": "PASS|WARN|FAIL",
  // PASS: >=2 nguồn độc lập xác nhận. WARN: 1 nguồn, hoặc chỉ nguồn không trusted.
  // FAIL: các nguồn mâu thuẫn nhau về claim này.
  "supporting_source_ids": [], "contradicting_source_ids": [],
  "explanation_vi": "1-2 câu"
}
Nếu không nguồn nào đề cập claim → WARN với explanation "không tìm thấy nguồn xác nhận".
```

## 5. `outline.generate` — tier `strong`

Biến: `topic`, `ranked_summaries` (top N source), `target_duration_s`, `claims_passed`

**Persona chung** (lặp lại nguyên văn ở đầu prompt 5/6/7 — 3 lời gọi LLM độc lập, có thể khác provider trong chain, nên phải tự mang theo persona thay vì kỳ vọng "nhớ" từ bước trước):
`Bạn là biên kịch video ngắn công nghệ tiếng Việt: giọng nói chuyện tự nhiên, nhịp nhanh, ưu tiên số liệu cụ thể, không giật tít sai sự thật.`

```
{{ persona }}

Lập dàn ý video {{ target_duration_s }} giây về "{{ topic }}" từ nghiên cứu sau:
{{ ranked_summaries }}

Chỉ dùng fact đã kiểm chứng: {{ claims_passed }}

Output JSON: { "outline": {
  "hook": "1-2 câu mở đầu — PHẢI là 1 trong 3 dạng: (a) số liệu gây bất ngờ,
           (b) câu hỏi phản trực giác, (c) mâu thuẫn/tranh cãi giữa các nguồn —
           dựa trên fact thật, kèm [source_id]. KHÔNG viết mô tả chung chung.",
  "introduction": "...", "problem": "...",
  "controversy": "quan điểm trái chiều giữa các nguồn nếu có, hoặc null —
                  KHÔNG bịa tranh cãi nếu các nguồn đồng thuận",
  "solution": "...",
  "demo": "ví dụ/số liệu minh hoạ cụ thể", "conclusion": "...",
  "cta": "kêu gọi hành động ngắn"
}}
Ngân sách từ theo phần (tổng ≈ {{ target_duration_s * 4 }} từ, ~{{ target_duration_s }}s đọc):
hook ≤15%, introduction+problem ~20%, controversy (nếu có) ~10%, demo ≥25%, phần còn lại chia đều.
Mỗi phần 1-3 câu.
```

## 6. `script.generate` — tier `strong`

Biến: `topic`, `outline_json`, `target_duration_s`

```
{{ persona }}

Viết kịch bản video từ dàn ý đã duyệt. Câu ngắn (dưới 20 từ) nhưng XEN vài câu trung bình
(12-20 từ) để tạo nhịp đọc tự nhiên — tránh mọi câu đều ngắn đều đều như liệt kê.
Số đọc được ("92,5 phần trăm" không phải "92.5%"). KHÔNG dùng emoji, KHÔNG dùng viết tắt
không đọc được (viết tắt phải phiên âm được, vd "AI" giữ nguyên vì đọc được, "vs." → "so với").

{{ outline_json }}

Output JSON: {
  "title": "≤70 ký tự, có từ khoá, không clickbait sai sự thật",
  "description": "2-3 câu + hashtag",
  "tags": ["5-10 tag"],
  "voice_over": "toàn bộ lời đọc, chia đoạn bằng \n\n theo ý",
  "estimated_duration_s": int
}
Giữ nguyên mọi số liệu từ outline — KHÔNG làm tròn, KHÔNG thêm fact mới.
```

## 7. `storyboard.generate` — tier `strong` — **Semantic Storyboard (AI KHÔNG chọn layout)**

Biến: `script_json`, `target_duration_s` *(không còn `layouts_available` — layout do Layout Engine quyết, xem [layout-engine.md](layout-engine.md))*

```
{{ persona }}

Chia kịch bản thành các cảnh video (mỗi cảnh 4-8 giây, tổng ≈ {{ target_duration_s }}s).
Bạn CHỈ mô tả NỘI DUNG và Ý ĐỒ từng cảnh — KHÔNG chọn bố cục, vị trí, font, hiệu ứng.

Kịch bản: {{ script_json.voice_over }}

Ví dụ 1 cảnh ĐÚNG (minh hoạ cách trích narration_anchor — không phải nội dung cần theo):
{"purpose": "evidence", "beat": "reveal",
 "narration": "SWE-bench của model mới đạt 92,5 phần trăm, tăng so với 74,9 phần trăm trước đó.",
 "components": [
   {"kind": "stat", "value": "92.5", "suffix": "%", "label": "SWE-bench (mới)", "source_id": "S1",
    "narration_anchor": "đạt 92,5 phần trăm"},
   {"kind": "stat", "value": "74.9", "suffix": "%", "label": "SWE-bench (cũ)", "source_id": "S1",
    "narration_anchor": "74,9 phần trăm trước đó"}
 ]}
narration_anchor LÀ CHUỖI CON Y HỆT của narration (đối chiếu ký tự) — không diễn giải lại,
không đổi thứ tự từ, không thêm/bớt dấu câu.

Output theo schema:
{ "scenes": [{
  "purpose": "hook|explain|evidence|compare|steps|quote|demo|conclusion|cta",
  "beat": "reveal|contrast|escalation|calm",   // nhịp điệu Ý ĐỒ của cảnh — không phải animation
  "narration": "phần lời đọc của cảnh này (chia trọn câu)",
  "components": [
    // mỗi component NÊN kèm "narration_anchor": trích đoạn ngắn trong narration
    // tương ứng với nó (để hệ thống đồng bộ thời điểm xuất hiện với giọng đọc)
    // chọn ĐÚNG loại component theo bản chất nội dung:
    {"kind": "heading", "text": "≤10 từ, **bold** từ khoá"},
    {"kind": "body", "text": "ý phụ ngắn"},
    {"kind": "media_intent", "query_vi": "mô tả hình cần có", "media_hint": "diagram|photo|screenshot|logo"},
    {"kind": "stat", "value": "92.5", "suffix": "%", "label": "SWE-bench", "source_id": "S1"},
    {"kind": "bullet", "text": "mỗi ý liệt kê 1 bullet"},
    {"kind": "chart_data", "unit": "%", "points": [{"label": "...", "value": ...}], "source_id": "S1"},
    {"kind": "table_data", "col_a": "...", "col_b": "...", "rows": [...], "source_id": "S1"},
    {"kind": "quote", "text": "...", "author": "...", "source_id": "S3"},
    {"kind": "code", "content": "...", "language": "..."},
    {"kind": "group", "label": "vế A", "children": [...]}  // dùng 2 group khi so sánh 2 vế
  ]
}]}
Quy tắc:
- Không lặp nguyên văn narration lên màn hình — rút gọn thành keyword/số liệu.
- stat/chart_data/table_data/quote BẮT BUỘC kèm source_id từ fact đã kiểm chứng.
- Một cảnh nói về 1 con số → dùng stat; liệt kê → bullet (3-6); so sánh 2 vế → 2 group.
- narration_anchor phải là TRÍCH ĐOẠN NGUYÊN VĂN từ narration (hệ thống match chính xác).
- Tối đa 8 component/cảnh; cảnh đầu purpose=hook, cảnh cuối purpose=cta.
- KHÔNG để 2 cảnh liên tiếp cùng purpose VÀ cùng component kind chủ đạo (vd 2 cảnh stat liền
  nhau) — đổi góc trình bày (bullet/compare/chart) để tránh đơn điệu.

TỰ KIỂM TRA trước khi trả JSON — nếu sai, sửa lại rồi mới xuất:
□ Mọi stat/chart_data/table_data/quote đều có source_id
□ Cảnh đầu purpose=hook, cảnh cuối purpose=cta
□ Không có 2 cảnh liên tiếp trùng purpose+component kind chủ đạo
□ Tổng ước lượng thời lượng các cảnh nằm trong ±10% target_duration_s
□ Mọi narration_anchor là chuỗi con nguyên văn của narration tương ứng
```

*(beat + narration_anchor là tín hiệu ngữ nghĩa cho Motion Planner — layout-engine.md §9. AI vẫn không chọn kiểu/thời điểm animation; anchor sai/thiếu → planner fallback theo thứ tự, không lỗi.)*

Sau đó **Layout Engine** (deterministic — [layout-engine.md](layout-engine.md)): Scene Tree → Semantic Analysis → Layout Classifier (rule table) → Constraint/Responsive/Theme/Motion → Scene JSON. AI không sinh Scene JSON, không chọn layout — cô lập hoàn toàn LLM khỏi quyết định bố cục.

## 8. `asset.query` — tier `cheap`

Biến: `media_query_vi` (từ component `media_intent.query_vi` trong semantic storyboard) + `media_hint`

```
Chuyển mô tả hình ảnh sau thành query tìm kiếm ảnh stock tiếng Anh (3-6 từ)
và 1 prompt sinh ảnh dự phòng. Loại hình mong muốn: {{ media_hint }}.
Mô tả: {{ media_query_vi }}
Output JSON: {"stock_query_en": "...", "generation_prompt_en": "...", "orientation": "vertical|horizontal"}
```

---

## Quản trị prompt

* Mỗi prompt seed là `version 1, is_active=true`. Sửa qua UI Admin → version mới; activate là thao tác riêng (FR-14).
* Đổi prompt phải chạy bộ **eval cố định** (10 topic mẫu trong `backend/tests/fixtures/eval_topics.json`) và so sánh output trước khi activate — checklist trong [test-plan.md](../test-plan.md).
* Biến `w_*` (trọng số ranking), `target_duration_s` đọc từ config hệ thống, không hardcode trong template.
