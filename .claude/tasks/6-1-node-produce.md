# Task 6-1: Node Produce — TTS batch + asset resolve

**Points:** 5đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 4-6, 2-4, 3-2 · **FR:** FR-19, FR-20

## User story
As a system, I want chuẩn bị đủ giọng đọc và ảnh có giấy phép cho mọi cảnh trước khi render, so that render không bao giờ chờ media và video không bao giờ dính ảnh mờ bản quyền.

## Why
Node "hậu cần" của pipeline — chậm nhất và dễ lỗi nhất. Thiết kế "lỗi cục bộ không giết run" (BR-3) là điều kiện để Mode 1 chạy đêm không người trông.

## Scope
**In:** TTS mọi cảnh song song bounded (semaphore/engine); điền `audio` vào scene JSON + validator nâng duration; asset resolve: `media_intent.query_vi` → prompt `asset.query` → asset chain (stock → SD local nếu active) → MinIO + license; thiếu → placeholder theme + cờ `asset_missing`; idempotent theo hash (audio + asset).
**Out:** BGM ingest (6-5); render (6-2); sinh ảnh nâng cao (chain lo).

## Business Rules
1. Chạy lại chỉ xử lý cảnh thiếu/stale (audio hash đổi khi voice text/giọng đổi — 5-2 BR-3).
2. Asset không rõ license → từ chối → provider kế → cuối cùng placeholder. Không bao giờ dùng ảnh thiếu license (see [rules/security.md](../rules/security.md)).
3. Lỗi 1 cảnh → cờ lỗi cảnh đó, cảnh khác tiếp tục; node fail chỉ khi >50% cảnh lỗi.
4. Ảnh stock chọn theo orientation khớp format project (dọc cho 9:16).
5. Audio produce xong → duration cảnh tự nâng nếu thiếu — ghi vào scene JSON version mới.
6. **(Motion pass-2)** sau TTS, gọi Motion Planner re-resolve `motion_plan` bằng word-timestamps thật (stat count-up kết thúc đúng lúc đọc xong số); chỉ cập nhật motion_plan — layout không đổi; deterministic, không token.

## Acceptance Criteria
1. **(happy)** 10 cảnh, chain pexels → đủ audio+timestamps; ≥8 ảnh thật đúng orientation; thiếu → placeholder + cờ.
2. **(biên/BR-1)** Run lần 2 → 0 call TTS/stock; sửa voice 1 cảnh → chỉ cảnh đó re-TTS.
3. **(biên/BR-3)** Mock TTS fail cảnh 3 → 9 cảnh xong, cảnh 3 cờ lỗi + retry riêng OK.
4. **(lỗi)** Mọi asset provider chết → toàn placeholder + cờ; run hoàn thành; UI cảnh báo tổng.
5. **(BR-2)** Provider trả ảnh không license (mock) → bị loại, thử provider kế.

## Data & API
Bảng: assets (ghi mới), scenes (update scene_json + hash). Events: step.progress. Contract change: không (schema audio field đã spec §3.4).

## Decisions already locked
- ⏳ Placeholder = nền gradient theme + icon chủ đề — video vẫn dùng được khi thiếu stock.
- ⏳ Ngưỡng fail node 50%.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + semaphore test (không vượt bound); idempotency test là trọng tâm.
