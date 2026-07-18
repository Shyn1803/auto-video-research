"""Seed data for the 8 prompts in docs/specs/prompts.md (Task 4-2 Step 2).

Templates are extracted programmatically (verbatim, including diacritics) from
the fenced code blocks in docs/specs/prompts.md -- do not hand-edit the template
strings below; regenerate them from the spec if it changes (dev-guide.md's
contract-change rule: the doc is the source of truth, this module is its
DB-loadable form).

``variables`` is the declared list checked by BR-3 (prompt_render.py) -- a
*superset* of what a template must reference is fine (over-declaring is not a
violation, using an undeclared variable at save time is the 400). Three prompts
reference variables the spec's short "Bien:" line doesn't spell out in full:
``ranking.score`` uses ``today``/``w_recency``/``w_relevance``/``w_trust``/
``w_confirm`` beyond its stated ``topic, sources_json``; ``outline.generate``/
``script.generate``/``storyboard.generate`` each use the shared ``persona``
block (per the spec's own note: 3 independent LLM calls, no shared memory, so
each "phai tu mang theo persona"). Declared explicitly here so seeding doesn't
400 against its own templates.
"""

from __future__ import annotations

from typing import TypedDict


class PromptSeed(TypedDict):
    name: str
    tier: str
    description: str
    template: str
    variables: list[str]


PROMPT_SEEDS: list[PromptSeed] = [
    {
        "name": "research.summarize",
        "tier": "cheap",
        "description": "Tom tat 1 bai bao thanh summary_vi + key_facts co so lieu.",
        "template": (
            "Bạn là trợ lý nghiên cứu công nghệ AI. Tóm tắt bài viết sau bằng tiếng Việt,\n"
            'phục vụ việc sản xuất video ngắn về chủ đề "{{ topic }}".\n\n'
            "Bài viết: {{ article_title }} ({{ source_url }})\n---\n"
            "{{ article_content }}\n---\n"
            'Yêu cầu output JSON:\n{\n'
            ' "summary_vi": "3-5 câu tóm tắt, tập trung thông tin MỚI và SỐ LIỆU cụ thể",\n'
            ' "key_facts": ["mỗi fact 1 câu, có số liệu/tên/ngày cụ thể nếu bài nêu"],\n'
            ' "relevance_to_topic": 0-10,\n'
            ' "published_info": {"date": "YYYY-MM-DD hoặc null", "author": "hoặc null"}\n'
            "}\n"
            "Chỉ dùng thông tin CÓ TRONG bài viết. Không suy diễn."
        ),
        "variables": ["topic", "article_title", "article_content", "source_url"],
    },
    {
        "name": "ranking.score",
        "tier": "cheap",
        "description": "Cham diem cac nguon tin theo do moi/lien quan/tin cay/xac nhan cheo.",
        "template": (
            'Chấm điểm các nguồn tin sau cho video về "{{ topic }}". Hôm nay: {{ today }}.\n'
            "Tiêu chí (trọng số): Độ mới ({{ w_recency }}), Liên quan ({{ w_relevance }}),\n"
            "Tin cậy ({{ w_trust }} — nguồn trusted/paper/blog chính thức cao hơn),\n"
            "Được xác nhận chéo ({{ w_confirm }} — nhiều nguồn nói cùng một việc).\n\n"
            "{{ sources_json }}\n\n"
            'Output JSON: {"rankings": [{"source_id": "...", "score": 0-100, "reason_vi": "1 câu"}]}'
        ),
        "variables": [
            "topic",
            "today",
            "w_recency",
            "w_relevance",
            "w_trust",
            "w_confirm",
            "sources_json",
        ],
    },
    {
        "name": "factcheck.extract_claims",
        "tier": "strong",
        "description": "Trich xuat cac claim kiem chung duoc tu script/summary.",
        "template": (
            "Trích xuất mọi CLAIM KIỂM CHỨNG ĐƯỢC từ nội dung sau (tên model, số benchmark,\n"
            "ngày phát hành, tên paper, repo github, số phiên bản, so sánh định lượng).\n"
            "Bỏ qua ý kiến chủ quan.\n\n"
            "{{ script_or_summary }}\n\n"
            'Output JSON: {"claims": [{"claim_text": "nguyên văn ngắn gọn",\n'
            ' "claim_type": "model_name|benchmark|release_date|paper|github|version|other"}]}'
        ),
        "variables": ["script_or_summary", "topic"],
    },
    {
        "name": "factcheck.verify_claim",
        "tier": "strong",
        "description": "Kiem chung 1 claim dua tren cac trich doan nguon (PASS/WARN/FAIL).",
        "template": (
            "Kiểm chứng claim sau dựa DUY NHẤT trên các trích đoạn nguồn cung cấp.\n\n"
            "CLAIM: {{ claim_text }}\n"
            "NGUỒN: {{ evidence_json }} // [{source_id, quote, source_trusted}]\n\n"
            'Output JSON: {\n'
            ' "verdict": "PASS|WARN|FAIL",\n'
            " // PASS: >=2 nguồn độc lập xác nhận. WARN: 1 nguồn, hoặc chỉ nguồn không trusted.\n"
            " // FAIL: các nguồn mâu thuẫn nhau về claim này.\n"
            ' "supporting_source_ids": [], "contradicting_source_ids": [],\n'
            ' "explanation_vi": "1-2 câu"\n'
            "}\n"
            'Nếu không nguồn nào đề cập claim → WARN với explanation "không tìm thấy nguồn xác nhận".'
        ),
        "variables": ["claim_text", "evidence_json"],
    },
    {
        "name": "outline.generate",
        "tier": "strong",
        "description": "Lap dan y video (hook/intro/problem/controversy/solution/demo/conclusion/cta).",
        "template": (
            "{{ persona }}\n\n"
            'Lập dàn ý video {{ target_duration_s }} giây về "{{ topic }}" từ nghiên cứu sau:\n'
            "{{ ranked_summaries }}\n\n"
            "Chỉ dùng fact đã kiểm chứng: {{ claims_passed }}\n\n"
            'Output JSON: { "outline": {\n'
            ' "hook": "1-2 câu mở đầu — PHẢI là 1 trong 3 dạng: (a) số liệu gây bất ngờ,\n'
            ' (b) câu hỏi phản trực giác, (c) mâu thuẫn/tranh cãi giữa các nguồn —\n'
            ' dựa trên fact thật, kèm [source_id]. KHÔNG viết mô tả chung chung.",\n'
            ' "introduction": "...",\n'
            ' "problem": "...",\n'
            ' "controversy": "quan điểm trái chiều giữa các nguồn nếu có, hoặc null —\n'
            ' KHÔNG bịa tranh cãi nếu các nguồn đồng thuận",\n'
            ' "solution": "...",\n'
            ' "demo": "ví dụ/số liệu minh hoạ cụ thể", "conclusion": "...",\n'
            ' "cta": "kêu gọi hành động ngắn"\n'
            "}\n}\n"
            "Ngân sách từ theo phần (tổng ≈ {{ target_duration_s * 4 }} từ, ~{{ target_duration_s }}s đọc):\n"
            "hook ≤15%, introduction+problem ~20%, controversy (nếu có) ~10%, demo ≥25%, phần còn lại chia đều.\n"
            "Mỗi phần 1-3 câu."
        ),
        "variables": [
            "persona",
            "topic",
            "ranked_summaries",
            "target_duration_s",
            "claims_passed",
        ],
    },
    {
        "name": "script.generate",
        "tier": "strong",
        "description": "Viet kich ban (title/description/tags/voice_over) tu outline da duyet.",
        "template": (
            "{{ persona }}\n\n"
            "Viết kịch bản video từ dàn ý đã duyệt. Câu ngắn (dưới 20 từ) nhưng XEN vài câu trung bình\n"
            "(12-20 từ) để tạo nhịp đọc tự nhiên — tránh mọi câu đều ngắn đều đều như liệt kê.\n"
            'Số đọc được ("92,5 phần trăm" không phải "92.5%"). KHÔNG dùng emoji, KHÔNG dùng viết tắt\n'
            'không đọc được (viết tắt phải phiên âm được, vd "AI" giữ nguyên vì đọc được, "vs." → "so với").\n\n'
            "{{ outline_json }}\n\n"
            'Output JSON: {\n'
            ' "title": "≤70 ký tự, có từ khoá, không clickbait sai sự thật",\n'
            ' "description": "2-3 câu + hashtag",\n'
            ' "tags": ["5-10 tag"],\n'
            ' "voice_over": "toàn bộ lời đọc, chia đoạn bằng \\n\\n theo ý",\n'
            ' "estimated_duration_s": int\n'
            "}\n"
            "Giữ nguyên mọi số liệu từ outline — KHÔNG làm tròn, KHÔNG thêm fact mới."
        ),
        "variables": ["persona", "outline_json", "target_duration_s"],
    },
    {
        "name": "storyboard.generate",
        "tier": "strong",
        "description": "Semantic Storyboard (AI khong chon layout) -- chia kich ban thanh cac canh voi component ngu nghia.",
        "template": (
            "{{ persona }}\n\n"
            'Chia kịch bản thành các cảnh video (mỗi cảnh 4-8 giây, tổng ≈ {{ target_duration_s }}s).\n'
            "Bạn CHỈ mô tả NỘI DUNG và Ý ĐỒ từng cảnh — KHÔNG chọn bố cục, vị trí, font, hiệu ứng.\n\n"
            "Kịch bản: {{ script_json.voice_over }}\n\n"
            'Ví dụ 1 cảnh ĐÚNG (minh hoạ cách trich narration_anchor — không phải nội dung cần theo):\n'
            '{"purpose": "evidence", "beat": "reveal",\n'
            ' "narration": "SWE-bench của model mới đạt 92,5 phần trăm, tăng so với 74,9 phần trăm trước đó.",\n'
            ' "components": [\n'
            ' {"kind": "stat", "value": "92.5", "suffix": "%", "label": "SWE-bench (mới)", "source_id": "S1",\n'
            '  "narration_anchor": "đạt 92,5 phần trăm"},\n'
            ' {"kind": "stat", "value": "74.9", "suffix": "%", "label": "SWE-bench (cũ)", "source_id": "S1",\n'
            '  "narration_anchor": "74,9 phần trăm trước đó"}\n'
            " ]}\n"
            "narration_anchor LÀ CHUỖI CON Y HỆT của narration (đối chiếu ký tự) — không diễn giải lại,\n"
            "không đổi thứ tự từ, không thêm/bớt dấu câu.\n\n"
            'Output theo schema:\n{ "scenes": [{\n'
            ' "purpose": "hook|explain|evidence|compare|steps|quote|demo|conclusion|cta",\n'
            ' "beat": "reveal|contrast|escalation|calm", // nhịp điệu Ý ĐỒ của cảnh — không phải animation\n'
            ' "narration": "phần lời đọc của cảnh này (chia trọn câu)",\n'
            ' "components": [\n'
            '  // mỗi component NÊN kèm "narration_anchor": trích đoạn ngắn trong narration\n'
            '  // tương ứng với nó (để hệ thống đồng bộ thời điểm xuất hiện với giọng đọc)\n'
            '  // chọn ĐÚNG loại component theo bản chất nội dung:\n'
            '  {"kind": "heading", "text": "≤10 từ, **bold** từ khoá"},\n'
            '  {"kind": "body", "text": "ý phụ ngắn"},\n'
            '  {"kind": "media_intent", "query_vi": "mô tả hình cần có", "media_hint": "diagram|photo|screenshot|logo"},\n'
            '  {"kind": "stat", "value": "92.5", "suffix": "%", "label": "SWE-bench", "source_id": "S1"},\n'
            '  {"kind": "bullet", "text": "mỗi ý liệt kê 1 bullet"},\n'
            '  {"kind": "chart_data", "unit": "%", "points": [{"label": "...", "value": ...}], "source_id": "S1"},\n'
            '  {"kind": "table_data", "col_a": "...", "col_b": "...", "rows": [...], "source_id": "S1"},\n'
            '  {"kind": "quote", "text": "...", "author": "...", "source_id": "S3"},\n'
            '  {"kind": "code", "content": "...", "language": "..."},\n'
            '  {"kind": "group", "label": "vế A", "children": [...]} // dùng 2 group khi so sánh 2 vế\n'
            " ]\n"
            "}]}\n"
            "Quy tắc:\n"
            "- Không lặp nguyên văn narration lên màn hình — rút gọn thành keyword/số liệu.\n"
            "- stat/chart_data/table_data/quote BẮT BUỘC kèm source_id từ fact đã kiểm chứng.\n"
            "- Một cảnh nói về 1 con số → dùng stat; liệt kê → bullet (3-6); so sánh 2 vế → 2 group.\n"
            "narration_anchor phải là TRÍCH ĐOẠN NGUYÊN VĂN từ narration (hệ thống match chính xác).\n"
            "- Tối đa 8 component/cảnh; cảnh đầu purpose=hook, cảnh cuối purpose=cta.\n"
            "KHÔNG để 2 cảnh liên tiếp cùng purpose VÀ cùng component kind chủ đạo (vd 2 cảnh stat liền\n"
            "nhau) — đổi góc trình bày (bullet/compare/chart) để tránh đơn điệu.\n\n"
            "TỰ KIỂM TRA trước khi trả JSON — nếu sai, sửa lại rồi mới xuất:\n"
            "□ Mọi stat/chart_data/table_data/quote đều có source_id\n"
            "□ Cảnh đầu purpose=hook, cảnh cuối purpose=cta\n"
            "Không có 2 cảnh liên tiếp trùng purpose+component kind chủ đạo\n"
            "□ Tổng ước lượng thời lượng các cảnh nằm trong ±10% target_duration_s\n"
            "□ Mọi narration_anchor là chuỗi con nguyên văn của narration tương ứng"
        ),
        "variables": ["persona", "script_json", "target_duration_s"],
    },
    {
        "name": "asset.query",
        "tier": "cheap",
        "description": "Chuyen mo ta hinh anh tieng Viet thanh stock query + generation prompt tieng Anh.",
        "template": (
            "Chuyển mô tả hình ảnh sau thành query tìm kiếm ảnh stock tiếng Anh (3-6 từ)\n"
            "và 1 prompt sinh ảnh dự phòng. Loại hình mong muốn: {{ media_hint }}.\n"
            "Mô tả: {{ media_query_vi }}\n"
            'Output JSON: {"stock_query_en": "...", "generation_prompt_en": "...", "orientation": "vertical|horizontal"}'
        ),
        "variables": ["media_query_vi", "media_hint"],
    },
    {
        "name": "research.ai_summary",
        "tier": "cheap",
        "description": "Tóm tắt 2 câu sau khi nghiên cứu xong (task 5-10).",
        "template": (
            'Tóm tắt nghiên cứu về "{{ topic }}" thành đúng 2 câu tiếng Việt, cắt ghọn, mỗi câu dưới 25 từ. '
            "Chỉ dùng thông tin sau, không suy diễn.\n\n"
            "{{ ranked_summaries }}\n\n"
            'Output JSON: {"ai_summary": "Câu 1. Câu 2."}'
        ),
        "variables": ["topic", "ranked_summaries"],
    },
]
