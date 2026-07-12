# Task 2-4: TTS adapter + edge-tts tiếng Việt

**Points:** 5đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 1-1 (parallel with 2-2/2-3) · **FR:** FR-19

## User story
As a Content Creator, I want giọng đọc tiếng Việt tự nhiên kèm timestamp từng từ, so that video có lời thuyết minh và phụ đề khớp mà không cần thu âm.

## Why
Giọng đọc là 50% chất lượng cảm nhận của video tin tức. edge-tts là lựa chọn 0đ tốt nhất cho tiếng Việt nhưng là service không chính thức → adapter interface là bảo hiểm (xem [patterns/provider-adapter.md](../patterns/provider-adapter.md)).

## Scope
**In:** `TTSAdapter` base (available/synthesize/ProviderError); adapter `edge_tts` (2 giọng, speed); MP3 + duration + word timestamps; cache MinIO theo hash(text+voice+speed+engine); mock adapter test; endpoint `POST scenes/{id}/tts-preview`.
**Out:** viXTTS/F5/FPT adapters (chèn theo docs/plan.md §5 khi cần); chuẩn hoá số→chữ (trách nhiệm prompt script 4-5 BR-2).

## Business Rules
1. Text rỗng/toàn khoảng trắng → lỗi validate, không gọi engine.
2. Text >500 ký tự → chia theo câu, ghép audio + nối timestamps offset chính xác.
3. Cache hit không gọi engine (counter đo được).
4. Lỗi engine → `ProviderError(retryable)` — adapter không tự retry (việc của router/node).
5. `voice_id` logic (`female_default`) map engine voice qua config — đổi engine không đổi dữ liệu scene.

## Acceptance Criteria
1. **(happy)** "Xin chào các bạn" nữ 1.0 → MP3 + timestamps từng từ; PO nghe duyệt chất lượng 3 câu mẫu.
2. **(biên/BR-2)** Đoạn 800 ký tự → 1 audio liền mạch, timestamps liên tục đúng offset.
3. **(biên/BR-3)** Gọi lần 2 cùng input → cache hit, engine counter không tăng.
4. **(lỗi/BR-4)** Engine 403 → ProviderError(retryable=true); mock node retry hoạt động.
5. **(BR-5)** Đổi config map voice → cùng scene ra giọng khác, không sửa scene JSON.

## Data & API
Storage: `audio/{project}/{hash}.mp3`. Endpoint mới: tts-preview (api-spec §6). Contract change: không.

## Decisions already locked
- 2 giọng v1 (nữ mặc định) — thêm giọng = config, không task mới.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + test edge-tts thật đánh dấu `@external` chạy nightly; PR dùng mock.
