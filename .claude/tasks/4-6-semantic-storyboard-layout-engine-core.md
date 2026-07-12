# Task 4-6: Semantic Storyboard + Layout Engine core (Tree → Analysis → Classifier → Resolve)

**Points:** 6đ (PO 2026-07-11: +1đ theo kiến trúc engine) · **Epic:** 4 — Pipeline AI · **Depends:** 4-5, 2-1 · **FR:** FR-07, FR-08

## User story
As a Content Creator, I want AI chỉ mô tả nội dung và ý đồ từng cảnh còn hệ thống tự quyết bố cục tối ưu, so that phân cảnh luôn hợp lệ, đa dạng và nhất quán — không phụ thuộc "gu chọn layout" thất thường của LLM.

## Why
Kiến trúc Gamma-style ([decisions/0008-layout-engine-deterministic.md](../decisions/0008-layout-engine-deterministic.md), PO 2026-07-11): **AI không chọn layout**. Dựng phần lõi engine: Semantic Storyboard → Scene Tree → Semantic Analysis → Layout Classifier (rule table) → tích hợp Constraint/Theme/Motion resolver (preset từ 2-2/2-6) → Scene JSON resolved. This is the single most-enforced architectural rule in the project — see [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md) and [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md) before writing any code here.

## Scope
**In:** prompt `storyboard.generate` semantic (10 kinds + `beat` + `narration_anchor` — `docs/specs/prompts.md` §7); Pydantic Scene Tree + validate giới hạn (≤8 comp, bullet 3-6, group ≤2); Semantic Analysis (profile + dominant); Layout Classifier theo rule table **config** + `layout_override`; **Motion Planner pass-1** (choreography rules, timing ước lượng, anchor match + fallback thứ tự); pipeline resolve gọi preset (2-2); lưu tree + resolved JSON (kèm motion_plan) trong scene_set version; warnings machine-readable; integration MockLLM full-pipeline CI.
**Out:** constraint presets/motion table cụ thể (2-2, 2-6); solver tổng quát + Gallery/Timeline class (v1.1); editor semantic (5-1 dùng tree qua form).

## Business Rules
1. AI không sinh layout/vị trí/font/animation — schema đầu ra prompt không có các field đó; xuất hiện → parse fail. **Hard-enforced, this is the anti-pattern this project has already hit once — see the [rules/naming.md](../rules/naming.md) layout drift incident.**
2. Ghép `narration` các cảnh == voice_over script (normalize) — lệch là bug engine, không ship.
3. Classifier deterministic: cùng tree → cùng class (property test); rule table là config có version, sửa không deploy.
4. scene_set resolved pass strict 100% — fail là bug engine.
5. `layout_override` của user thắng classifier; regenerate: cấu trúc semantic cùng loại → giữ override, đổi loại → reset + thông báo.
6. Component kind dữ liệu (stat/chart/table/quote) thiếu source_id → strict chặn / auto_fix hạ về body + warning.
7. Cảnh >10s → tách tại ranh giới câu; class không khả dụng → hạ bậc theo bảng + warning.
8. **(Motion Planner)** deterministic theo rule §9.2; `narration_anchor` không match nguyên văn → bỏ anchor + fallback thứ tự (warning, không lỗi); attention budget (≤1 chuyển động lớn cùng lúc); mọi track khai `reason` (narration_sync|hierarchy|sequence).
9. **(chống lặp bố cục — video-taste.md §4.2)** post-pass sau classify: không quá 2 cảnh liên tiếp cùng class; 1 class không vượt 40% tổng cảnh (trừ Hero/TextFocus ≤2); video ≥8 cảnh phải ≥4 class khác nhau. **Luật engine, KHÔNG đưa vào prompt AI.**

## Acceptance Criteria
1. **(happy)** Script 60s → 8-12 cảnh: tree hợp lệ, class phân bổ đa dạng đúng rule, resolved strict-valid, đủ 2 format từ 1 tree (không gọi lại AI).
2. **(biên/BR-3)** Property test: 50 tree fixture → classifier ổn định.
3. **(biên/BR-5)** Override List→Quote, regenerate cùng cấu trúc → giữ Quote; đổi cảnh chart → reset + thông báo.
3b. **(biên/BR-9)** Fixture 10 cảnh mà classifier tự nhiên cho 4 cảnh MediaText liên tiếp → post-pass phân bổ lại.
4. **(biên/BR-1)** Mock LLM trả field "layout" → parse fail đúng BR.
5. **(BR-2)** Test ghép narration == voice_over pass 10 fixture.
6. **(CI)** Full pipeline MockLLM xanh; 3 topic thật Ollama nghiệm thu tay.

## Data & API
scenes lưu `semantic_tree` + resolved JSON + `layout_override`. Contract change: **có** — schema scene mở rộng; prompt schema mới.

## Decisions already locked
- Kiến trúc Layout Engine tầng, AI dừng ở semantic (PO 2026-07-11 — [decisions/0008](../decisions/0008-layout-engine-deterministic.md)).
- Rule table khởi điểm 12 rule; Gallery hạ về MediaText ở v1. ⏳ thứ tự rule do BA review khi implement.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixture profile→class là tài sản test trung tâm (mỗi rule ≥2 fixture); golden test: 5 semantic tree chuẩn → snapshot resolved JSON.
