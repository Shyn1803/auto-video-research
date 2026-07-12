# Epic 4 — Pipeline AI Mode 2: LangGraph + điều khiển run (FR-02→07, FR-14)

**Goal:** M3 — topic → scene_set qua 6 node có human gate; huỷ/ngầm/resume được; MockLLM CI xanh.
**Points:** 33 · **Tuần:** 5–8 · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO.

---

# Story 4.1 — LangGraph skeleton + checkpoint + human gate (5đ)

**User story:** As a system, I want pipeline có checkpoint bền và điểm dừng chờ người duyệt, so that crash không mất việc đã làm và user kiểm soát từng bước như SRS cam kết.
**Bối cảnh & giá trị:** Đây là bộ khung của toàn bộ giá trị sản phẩm (human-in-the-loop + resume — nguyên tắc thiết kế #1 và #4 của SRS). Mọi node sau chỉ là "điền thịt" vào khung này.

## Scope
**In:** graph 6 node (produce/render stub); state Pydantic→JSONB; checkpoint `langgraph-checkpoint-postgres`; interrupt sau mỗi node (Mode 2); map node↔state machine (1.4); API `steps/{step}/run` + `approve` + `GET runs/{id}`; retry backoff/node (3 lần); correlation_id = run_id xuyên log/event.
**Out:** logic node thật (4.3–4.6); cancel (4.7); mode không-interrupt (7.2).

## Business Rules
- **BR-1:** một project chỉ 1 run active — POST run khi đang chạy → 409.
- **BR-2:** approve chỉ hợp lệ khi run interrupt đúng node đó (chống double-approve/race — kiểm bằng checkpoint state).
- **BR-3:** node hoàn thành → checkpoint + step_version ghi **cùng transaction** (atomic — không bao giờ lệch nhau).
- **BR-4:** retry hết 3 lần → project FAILED(reason=node lỗi cuối), giữ previous_status (1.4 BR-3).

## UI/UX
Tiêu thụ bởi PipelineStepper (trạng thái run/attention) + RunningState (5.8). SSE `step.progress` phát từ node context.

## Data & API
- Bảng: `langgraph_checkpoints` (lib tự tạo qua migration); runs tracked qua checkpoint + status_history.
- Endpoints: §2 api-spec (run/approve/runs). Contract change: không.

## Acceptance Criteria
1. **(happy)** Run → interrupt sau research → project NEED_REVIEW → approve → node kế chạy; SSE đủ chuỗi sự kiện.
2. **(biên)** Kill process giữa node write → restart → resume đúng write; research không chạy lại (đo bằng call counter).
3. **(lỗi/BR-1,2)** POST run khi đang chạy → 409; approve node đã qua → 409.
4. **(biên/BR-3)** Giả lập crash giữa "node xong, đang ghi" → sau restart: checkpoint và step_version nhất quán (cùng có hoặc cùng không).
5. **(CI)** Integration skeleton node-stub xanh.

## Test Notes
Test BR-3 bằng fault injection (raise sau khi ghi 1 trong 2). Test resume là test quan trọng nhất — chạy trong CI mỗi PR đụng pipeline.

## Quyết định đã chốt
- Interrupt sau **mọi** node ở Mode 2 kể cả produce (user có thể muốn xem asset/audio trước render) — khớp wireframe. ⏳

**Depends:** 1.4, 1.5, 1.6, 3.2 · **Design:** PipelineStepper §3.2 · **FR:** AR-2

---

# Story 4.2 — Prompt Management + seed (3đ)

**User story:** As an Admin, I want prompt lưu DB có version và kích hoạt được không cần deploy, so that tune chất lượng tiếng Việt liên tục — việc sẽ làm hàng tuần trong 3 tháng đầu.
**Bối cảnh & giá trị:** FR-14. Chất lượng nội dung Việt phụ thuộc prompt nhiều hơn model; chu kỳ tune phải tính bằng phút (sửa → eval → activate), không bằng ngày (sửa code → deploy).

## Scope
**In:** bảng prompts/prompt_versions; seed 8 prompt từ [prompts.md](../specs/prompts.md); Jinja2 render + validate biến khai báo; `get_active_prompt(name)` cache invalidate-on-activate; tab Quản trị › Prompts (list/editor/diff 2 version/activate/rollback); CLI `make prompt-eval`.
**Out:** A/B prompt (v1.1); eval tự chấm bằng LLM (v1.1); prompt per-project (không có — hệ thống chung).

## Business Rules
- **BR-1:** đúng 1 version active/prompt (DB partial unique index).
- **BR-2:** activate bản chưa chạy eval → dialog cảnh báo, không chặn cứng (trust admin, ghi audit).
- **BR-3:** template dùng biến ngoài `variables[]` → 400 khi lưu, chỉ đúng biến thiếu.
- **BR-4:** node không hardcode prompt — CI grep chuỗi template trong `pipeline/` → fail.
- **BR-5:** rollback = activate version cũ (không tạo bản sao — lịch sử thẳng).

## UI/UX
- Màn: wireframe **Quản trị › Prompts**. States: default · loading · empty N/A (seed luôn có) · error banner · disabled (nút Activate disabled khi đang active + tooltip).
- A11y: editor textarea có label; diff view đọc được (thêm/xoá có prefix text không chỉ màu).

## Data & API
- Bảng: prompts/prompt_versions (schema §2.7). Endpoints §9. Contract change: không.

## Acceptance Criteria
1. **(happy)** Sửa script.generate → v2 → activate → call kế dùng v2 (không restart); rollback v1 OK.
2. **(biên/BR-3)** Lưu template có `{{ bien_la }}` → 400 nêu đúng biến.
3. **(quyền)** Creator → 403; audit ghi ai activate lúc nào.
4. **(eval)** `make prompt-eval PROMPT=script.generate V=2` xuất bảng so sánh 10 topic (độ dài, parse ok, giữ số liệu).
5. **(BR-1)** Race 2 activate đồng thời → 1 thắng, constraint giữ đúng 1 active.

## Test Notes
Fixture eval_topics.json 10 topic là tài sản dùng lâu dài — chọn topic đa dạng (model mới, công cụ, khái niệm, tin tức).

## Quyết định đã chốt
- Eval là bước khuyến nghị mạnh, không bắt buộc cứng (BR-2) — tốc độ tune quan trọng giai đoạn đầu (PO qua thiết kế FR-14).

**Depends:** 4.1 · **Design:** wireframe **Quản trị › Prompts** · **FR:** FR-14

---

# Story 4.3 — Node Research: thu thập + dedupe + tóm tắt (5đ)

**User story:** As a Content Creator, I want AI tự gom và tóm tắt nguồn từ nhiều kênh uy tín trong vài phút, so that tôi bắt đầu từ nguyên liệu đã sàng lọc thay vì tự Google cả buổi.
**Bối cảnh & giá trị:** FR-02 — bước tạo ra "nguyên liệu tin cậy" cho mọi bước sau. Chiến lược API/RSS-first (không crawl bừa) vừa là chất lượng vừa là pháp lý (robots/ToS đã cam kết trong SRS).

## Scope
**In:** connectors arXiv/HN-Algolia/GitHub/RSS-list(config)/SearXNG(+Tavily/Brave qua chain) — mỗi connector 1 module + fixture; crawl trafilatura (respect robots); paywall → title+abstract + `partial_content`; dedupe url_hash + embedding similarity; summarize song song bounded (tier cheap, prompt `research.summarize`); trusted domains seed; API sources đầy đủ (§4); SSE progress ("đang đọc X 4/12").
**Out:** UI màn (5.6); Reddit RSS (connector sau); quản lý RSS list qua UI (v1.1 — config file).

## Business Rules
- **BR-1:** 1 connector lỗi → skip + ghi nhận trong kết quả; run fail chỉ khi **mọi** connector lỗi.
- **BR-2:** similarity ≥ ngưỡng (config 0.92) → giữ bản trusted hơn, hoà thì mới hơn.
- **BR-3:** cache chung theo content_hash (project_id NULL) — không re-crawl URL đã có trong TTL 30 ngày.
- **BR-4:** giữ tối đa N source (config 20) theo ranking sơ bộ (mới + trusted).
- **BR-5:** summarize fail 1 bài → bài đó không summary + cờ, không chặn node (tối thiểu 5 bài thành công).

## UI/UX
UI ở 5.6; node cung cấp progress message có ý nghĩa (tên nguồn đang đọc) — không "Processing...".

## Data & API
- Bảng: sources, source_embeddings (schema §2.4). Endpoints §4. Events: step.progress.
- Contract change: không.

## Acceptance Criteria
1. **(happy)** Fixture 12 bài (2 trùng nội dung, 1 paywall) → 10 sources; partial đánh dấu; đủ summary_vi + key_facts.
2. **(biên/BR-1)** Mock HN timeout → run xong, kết quả ghi "HN không truy cập được"; các nguồn khác đủ.
3. **(biên/BR-3)** Re-run cùng topic → 0 re-crawl URL cũ (counter), nguồn mới vẫn thêm.
4. **(lỗi)** Mọi connector fail → node fail retryable, message "không thu thập được nguồn".
5. **(BR-2)** 2 bài giống 0.95 (1 trusted 1 không) → giữ trusted.
6. **(SSE)** Progress hiện tên nguồn thật.

## Test Notes
Fixture HTML 5 provider khác nhau (test-plan §3); connector test độc lập từng module; embedding similarity dùng fixture cặp câu 3.3.

## Quyết định đã chốt
- Ngưỡng similarity 0.92 khởi điểm — tune sau 2 tuần dogfooding bằng số liệu. ⏳
- RSS list khởi điểm: OpenAI/Anthropic/Google/DeepMind/NVIDIA/HuggingFace blog (SRS FR-02).

**Depends:** 4.1, 3.3 · **Design:** — (UI 5.6) · **FR:** FR-02

---

# Story 4.4 — Node Ranking + FactCheck (5đ)

**User story:** As a Content Creator, I want mọi thông tin quan trọng được kiểm chéo giữa các nguồn độc lập, so that video không bao giờ nói sai tên, số, ngày — thứ giết uy tín kênh nhanh nhất.
**Bối cảnh & giá trị:** FR-03/04 — lý do tồn tại của sản phẩm so với "ChatGPT viết kịch bản". Gate PASS/WARN/FAIL đã đặc tả định lượng trong SRS; story này hiện thực nó thành dữ liệu claim-level có evidence.

## Scope
**In:** ranking (prompt `ranking.score`, trọng số config) → score/reason vào source; factcheck: extract claims (`factcheck.extract_claims`) → gom evidence (embedding search trích đoạn liên quan từ sources) → verdict/claim (`factcheck.verify_claim`); verdict tổng + gate (FAIL→NEED_REVIEW+notify); API claims + override (§5); fixture kịch bản mâu thuẫn.
**Out:** UI (5.6); notify channel thật (7.4 — tạm log); re-check tự động theo chu kỳ (không có v1).

## Business Rules
- **BR-1:** PASS cần ≥2 nguồn **độc lập** — khác root domain; 2 bài cùng blog = 1 nguồn.
- **BR-2:** evidence từ source `partial_content` không đủ cho PASS (tối đa WARN).
- **BR-3:** override ghi audit, không xoá evidence; verdict tổng tính lại đồng bộ trong cùng request; response trả overall mới + claims bị ảnh hưởng.
- **BR-4:** claim không tìm được evidence → WARN "không tìm thấy nguồn xác nhận".
- **BR-5:** disable/xoá source → mọi claim có evidence từ nó tính lại verdict (đồng bộ, cùng response — 5.6 BR-4 tiêu thụ).
- **BR-6:** claim types theo spec (model_name/benchmark/release_date/paper/github/version/other); extraction bỏ ý kiến chủ quan.

## UI/UX
UI ở 5.6. Node bảo đảm dữ liệu evidence đủ giàu: quote nguyên văn + source_id + supports.

## Data & API
- Bảng: claims (schema §2.4). Endpoints §5.
- Contract change: **có** — response override/patch-source thêm `overall_verdict` + `affected_claims[]` (BR-3/5) → cập nhật api-spec §5 trong PR.

## Acceptance Criteria
1. **(happy)** Fixture 2 nguồn lệch ngày → claim FAIL + evidence 2 phía; project NEED_REVIEW; notify (log) bắn.
2. **(biên/BR-1)** 2 bài cùng openai.com xác nhận → WARN, không PASS.
3. **(biên/BR-5)** Disable nguồn evidence duy nhất của claim PASS → claim WARN, response chứa affected_claims.
4. **(override/BR-3)** Chọn giá trị đúng + lý do → verdict đổi + overall mới cùng response; audit query được.
5. **(BR-4)** Claim mồ côi → WARN đúng message.
6. **(quyền)** Creator không owner → 403.

## Test Notes
Fixture mâu thuẫn là tài sản test quan trọng (dùng cho 5.6, 7.2, E2E). Kiểm chất lượng extraction bằng eval tay 3 topic thật trong PR (bảng claim trích được vs mong đợi).

## Quyết định đã chốt
- WARN không chặn duyệt; video tự thêm "theo nguồn chưa xác nhận" (PO 2026-07-10).
- Trọng số ranking mặc định: mới 0.3 / liên quan 0.3 / tin cậy 0.25 / xác nhận chéo 0.15. ⏳

**Depends:** 4.3 · **Design:** — (UI 5.6) · **FR:** FR-03, FR-04

---

# Story 4.5 — Node Write: outline + script (3đ)

**User story:** As a Content Creator, I want dàn ý rồi kịch bản tiếng Việt có dẫn nguồn từng phần, so that tôi chỉ biên tập thay vì viết từ đầu, và luôn truy được mọi câu về nguồn.
**Bối cảnh & giá trị:** FR-05/06. Ràng buộc "chỉ dùng fact đã kiểm chứng" là điểm nối giữa fact-check và nội dung — nơi hallucination bị chặn lần cuối trước khi thành lời đọc.

## Scope
**In:** outline (prompt §5 — 7 phần, dẫn [source_id], chỉ claim PASS/WARN-đã-duyệt); script (prompt §6 — giữ số liệu; check tự động tập số outline ⊆ script, lệch → retry 1 → cờ warning); 2 sub-step approve riêng; PUT version sửa tay.
**Out:** UI (5.7); tone/style tuỳ chọn (v1.1 — 1 tone chuẩn theo prompt).

## Business Rules
- **BR-1:** claim FAIL "loại khỏi video" → nội dung đó không xuất hiện outline/script (lọc context trước prompt).
- **BR-2:** voice_over viết số thành chữ đọc được; validator cảnh báo nếu còn ký hiệu (%/$) trong voice_over → cờ warning.
- **BR-3:** title >70 ký tự → cắt thông minh tại ranh giới từ + cờ cho user xem (không âm thầm).
- **BR-4:** claim WARN dùng trong script → câu đó kèm "theo nguồn chưa xác nhận" (prompt yêu cầu; validator kiểm sự hiện diện).

## UI/UX
UI 5.7; cờ warning của node phải machine-readable (`warnings: [{type, detail}]` trong version content) để UI render banner đúng chỗ.

## Data & API
- Dữ liệu: step_versions (outline, script) + warnings trong content JSONB.
- Contract change: **có** — chuẩn hoá `warnings[]` trong content version → ghi vào api-spec §3 (dạng content mỗi step).

## Acceptance Criteria
1. **(happy)** Outline 7 phần đủ [source_id]; script đúng cấu trúc; tập số khớp.
2. **(biên/BR-1)** Claim FAIL bị loại → không xuất hiện trong outline (test theo từ khoá claim).
3. **(biên/BR-4)** Claim WARN được dùng → câu chứa "theo nguồn chưa xác nhận".
4. **(lỗi/BR-2,3)** Script lệch số sau retry → version có warnings; title dài → cắt + warning.
5. **(version)** Sửa outline tay → script sinh từ bản sửa (parent đúng — 1.5 BR-5).

## Test Notes
Check "tập số ⊆" là pure function — unit kỹ (định dạng 92,5 vs 92.5 vs chín-hai-phẩy-năm: so sánh sau chuẩn hoá).

## Quyết định đã chốt
- Không chặn cứng khi lệch số sau retry — con người quyết (cờ warning + UI nêu rõ), tránh pipeline kẹt vì LLM local yếu. ⏳

**Depends:** 4.4, 4.2 · **Design:** — (UI 5.7) · **FR:** FR-05, FR-06

---

# Story 4.6 — Semantic Storyboard + Layout Engine core (Tree → Analysis → Classifier → Resolve) (6đ — +1đ theo kiến trúc engine, PO 2026-07-11)

**User story:** As a Content Creator, I want AI chỉ mô tả nội dung và ý đồ từng cảnh còn hệ thống tự quyết bố cục tối ưu, so that phân cảnh luôn hợp lệ, đa dạng và nhất quán — không phụ thuộc "gu chọn layout" thất thường của LLM.
**Bối cảnh & giá trị:** Kiến trúc Gamma-style ([layout-engine.md](../specs/layout-engine.md), quyết định PO 2026-07-11): **AI không chọn layout**. Story này dựng phần lõi engine: Semantic Storyboard (prompt mới §7) → Scene Tree → Semantic Analysis → Layout Classifier (rule table) → tích hợp Constraint/Theme/Motion resolver (preset từ 2.2/2.6) → Scene JSON resolved. Toàn bộ sau AI là pure function — đổi format/theme không tốn token.

## Scope
**In:** prompt `storyboard.generate` semantic (10 kinds + `beat` + `narration_anchor` — prompts.md §7); Pydantic Scene Tree + validate giới hạn (≤8 comp, bullet 3–6, group ≤2); Semantic Analysis (profile + dominant); Layout Classifier theo rule table **config** (layout-engine §5) + `layout_override`; **Motion Planner pass-1** (choreography rules §9.2, timing ước lượng, anchor match + fallback thứ tự); pipeline resolve gọi preset (2.2); lưu tree + resolved JSON (kèm motion_plan) trong scene_set version; warnings machine-readable; integration MockLLM full-pipeline CI.
**Out:** constraint presets/motion table cụ thể (2.2, 2.6); solver tổng quát + Gallery/Timeline class (v1.1); editor semantic (5.1 dùng tree qua form).

## Business Rules
- **BR-1:** AI không sinh layout/vị trí/font/animation — schema đầu ra prompt không có các field đó; xuất hiện → parse fail.
- **BR-2:** ghép `narration` các cảnh == voice_over script (normalize) — lệch là bug engine, không ship.
- **BR-3:** classifier deterministic: cùng tree → cùng class (property test); rule table là config có version, sửa không deploy.
- **BR-4:** scene_set resolved pass strict 100% — fail là bug engine.
- **BR-5:** `layout_override` của user thắng classifier; regenerate nội dung: cấu trúc semantic cùng loại → giữ override, đổi loại → reset + thông báo.
- **BR-6:** component kind dữ liệu (stat/chart/table/quote) thiếu source_id → strict chặn / auto_fix hạ về body + warning (nối 2.6 BR-2).
- **BR-7:** cảnh >10s → tách tại ranh giới câu; class không khả dụng (Gallery v1) → hạ bậc theo bảng + warning.
- **BR-8 (Motion Planner):** planner deterministic theo rule §9.2; `narration_anchor` không match nguyên văn narration → bỏ anchor đó + fallback thứ tự (warning, không lỗi); attention budget enforce (≤1 chuyển động lớn cùng lúc); mọi track khai `reason` (narration_sync|hierarchy|sequence) — thiếu reason là bug engine.
- **BR-9 (chống lặp bố cục — video-taste.md §4.2, mới):** post-pass sau khi mọi cảnh classify: không quá 2 cảnh liên tiếp cùng class; 1 class không vượt 40% tổng cảnh (trừ Hero/TextFocus ≤2 cảnh); video ≥8 cảnh phải ≥4 class khác nhau — không đạt thì warning, không tự sửa vòng lặp. Đây là luật engine, KHÔNG đưa vào prompt AI.

## UI/UX
Đầu vào màn Phân cảnh; gallery layout trong editor = **override UI** của classifier (nhãn "Tự động (List) ▾" + các lựa chọn khác). Warnings banner như 5.7.

## Data & API
- scenes lưu `semantic_tree` + resolved JSON + `layout_override` → **cập nhật scene-json-schema (đã làm) + database-schema (cột jsonb tree, cột override)**.
- Contract change: **có** — schema scene mở rộng; prompt schema mới.

## Acceptance Criteria
1. **(happy)** Script 60s → 8–12 cảnh: tree hợp lệ, class phân bổ đa dạng đúng rule (cảnh hook→Hero, stat→BigNumber…), resolved strict-valid, đủ 2 format từ 1 tree (không gọi lại AI — đo call counter).
2. **(biên/BR-3)** Property test: 50 tree fixture → classifier ổn định, đổi thứ tự component không đổi class.
3. **(biên/BR-5)** Override List→Quote, regenerate cùng cấu trúc → giữ Quote; đổi thành cảnh chart → reset + thông báo.
3b. **(biên/BR-9)** Fixture 10 cảnh mà classifier tự nhiên cho 4 cảnh MediaText liên tiếp → post-pass phân bổ lại, không cảnh nào >2 liên tiếp cùng class; video 8 cảnh chỉ 2 class → warning hiển thị.
4. **(biên/BR-1)** Mock LLM trả field "layout" → parse fail đúng BR (retry rồi lỗi rõ).
5. **(BR-2)** Test ghép narration == voice_over pass 10 fixture.
6. **(CI)** Full pipeline MockLLM xanh; 3 topic thật Ollama nghiệm thu tay (bảng class được chọn vs kỳ vọng BA).

## Test Notes
Classifier + analysis là pure function — bộ fixture profile→class là tài sản test trung tâm (mỗi rule ≥2 fixture: match + không match). Golden test: 5 semantic tree chuẩn → snapshot resolved JSON.

## Quyết định đã chốt
- Kiến trúc Layout Engine tầng, AI dừng ở semantic (PO 2026-07-11 — ADR-8).
- Rule table khởi điểm 12 rule theo layout-engine §5; Gallery hạ về MediaText ở v1. ⏳ thứ tự rule do BA review khi implement.

**Depends:** 4.5, 2.1 · **Design:** — · **FR:** FR-07, FR-08

---

# Story 4.7 — Điều khiển run: huỷ / chạy ngầm / resume (3đ) 🆕

**User story:** As a Content Creator, I want huỷ một bước AI đang chạy hoặc để nó chạy ngầm, so that tôi không bị giam trong màn chờ khi đổi ý hoặc muốn làm việc khác.
**Bối cảnh & giá trị:** Gap từ design-critique: RunningState có nút Huỷ nhưng không API nào đứng sau. Không có story này, cách duy nhất dừng một run sai là chờ nó chạy hết (tốn quota + thời gian).

## Scope
**In:** `POST runs/{id}/cancel`; abort an toàn (kết thúc sau LLM call hiện tại — không giết giữa transaction BR 4.1-3); cạnh state machine RUNNING→CANCELLED (+previous_status); resume sau cancel = run mới từ checkpoint; "chạy ngầm" = FE rời màn (SSE sẵn — không API mới).
**Out:** pause/resume giữa node (checkpoint đủ); huỷ hàng loạt (không cần).

## Business Rules
- **BR-1:** cancel best-effort có xác nhận: trạng thái CANCELLED chỉ khi node dừng thật (event xác nhận); UI hiện "đang huỷ…" trong lúc chờ (tối đa ~30s = 1 LLM call).
- **BR-2:** chi phí đã phát sinh vẫn ghi usage.
- **BR-3:** cancel không xoá version đã tạo trước đó.
- **BR-4:** cancel run đã kết thúc → 409.

## UI/UX
Nút Huỷ trong RunningState (5.8 render); confirm khi run >30s ("giữ kết quả các bước đã xong"). State "đang huỷ" là sub-state của RunningState.

## Data & API
- Cạnh mới state machine (cập nhật ma trận 1.4 + test); endpoint mới → **cập nhật api-spec §2**.
- Event mới: `run.cancelled` → **cập nhật event-catalog**.

## Acceptance Criteria
1. **(happy)** Cancel giữa research → "đang huỷ…" → CANCELLED ≤30s; resume → run mới tiếp từ checkpoint.
2. **(biên)** Cancel đúng lúc node vừa xong → run kết thúc bình thường tại interrupt (không race, không CANCELLED sai).
3. **(lỗi/BR-4)** Cancel run xong → 409.
4. **(UI)** Rời màn khi chạy → dashboard card ●%; quay lại đúng RunningState; sau cancel card hiện "Đã huỷ — chạy tiếp?".

## Test Notes
Race test (cancel vs node-finish) chạy lặp 20 lần trong CI (flaky-hunter). Fault injection giữa transaction xác nhận BR 4.1-3 giữ vững.

## Quyết định đã chốt
- Không hard-kill LLM call đang bay (chờ xong call hiện tại) — đơn giản, an toàn transaction; trade-off chờ tối đa ~30s ghi rõ trong UI. ⏳

**Depends:** 4.1 · **Design:** RunningState §3.4 · **FR:** NFR-3

---

# Story 4.8 — Điểm vào "Có sẵn kịch bản" (3đ) 🆕

**User story:** As a Content Creator, I want dán kịch bản tôi đã viết sẵn và đi thẳng tới dựng cảnh, so that video từ script có sẵn mất vài phút thay vì đi qua 2 bước nghiên cứu–viết không cần thiết.
**Bối cảnh & giá trị:** Use case thực tế phổ biến: creator đã có script (tự viết / từ nơi khác). Pipeline mặc định ép Research→Nội dung là 2 bước thừa với họ. Quyết định giữ nguyên hàng rào: **fact-check vẫn chạy trên script dán vào** — không có đường nào ra video mà bỏ qua kiểm chứng.

## Scope
**In:** nhánh "Có sẵn kịch bản" trong modal Tạo dự án (thay nhánh "tạo trống" — đã bỏ); graph entry thứ 2: script → extract claims → factcheck (evidence tìm qua search với claim làm query) → gate như thường → storyboard; script dán lưu thành script v1 (created_by=user); title/description/tags sinh bằng AI từ script (sub-step nhẹ, sửa được); trạm Nghiên cứu + Nội dung trên stepper hiển thị trạng thái "bỏ qua có kiểm chứng" (tooltip giải thích).
**Out:** import file docx/URL (v1.1 — v1 chỉ paste text); dịch script ngôn ngữ khác (ngoài scope); nhảy thẳng tới scene JSON (không — storyboard vẫn chạy).

## Business Rules
- **BR-1:** fact-check bắt buộc — claim FAIL vẫn chặn như luồng thường; evidence tìm bằng search chain (không có sẵn sources).
- **BR-2:** script dán 100–3000 ký tự; ngoài khoảng → validate với hướng dẫn.
- **BR-3:** stepper: Nghiên cứu hiển thị "— bỏ qua", Nội dung hiển thị "✓ từ kịch bản của bạn" — user vẫn click vào Nội dung để sửa script (quay lại luồng thường từ đó, versioning nguyên vẹn).
- **BR-4:** project đánh dấu `entry_point=script` (phân tích 8.7 tách nhóm này khi so hiệu quả).

## UI/UX
- Modal Tạo dự án khối dưới (wireframe); sau tạo → RunningState "Đang kiểm chứng kịch bản…" → Phân cảnh. States: validate lỗi inline; fact-check FAIL → NEED_REVIEW mở tab Kiểm chứng như thường.
- A11y: textarea label + đếm ký tự.

## Data & API
- `projects.entry_point` (cột mới, migration); `POST /projects` nhận `script_text?` → **cập nhật api-spec §2 + database-schema**.
- Graph: conditional entry (LangGraph branch) — không node mới, tái dùng factcheck/storyboard.
- Contract change: **có** — field tạo project + cột.

## Acceptance Criteria
1. **(happy)** Dán script 800 ký tự → kiểm chứng chạy → Phân cảnh có scene_set; title/tags đã sinh; script v1 created_by=user.
2. **(biên/BR-1)** Script chứa claim sai (fixture) → FAIL → NEED_REVIEW, xử lý bằng UI 5.6 như luồng thường.
3. **(biên/BR-3)** Click trạm Nội dung sau khi vào từ script → sửa được, tạo v2, storyboard stale đúng cascade.
4. **(lỗi/BR-2)** Script 50 ký tự → chặn kèm hướng dẫn.
5. **(quyền)** Như luồng tạo project thường.

## Test Notes
Fixture script có 2 claim (1 đúng 1 sai); integration entry-branch với MockLLM thêm vào bộ CI pipeline.

## Quyết định đã chốt
- Thay nhánh "tạo trống" bằng nhánh này (PO duyệt 2026-07-11 — "tạo trống" mơ hồ, ít giá trị).
- Fact-check không thể bỏ qua kể cả entry này (nguyên tắc SRS #5).

**Depends:** 4.4, 4.6, 1.3 · **Design:** wireframe **Tạo dự án** khối dưới · **FR:** FR-06, Mode 2

---

## 🏁 M3 (cuối tuần 8)
3 topic thật → scene_set; review UI đủ (5.6/5.7); CI MockLLM xanh; demo huỷ/resume cho PO.
