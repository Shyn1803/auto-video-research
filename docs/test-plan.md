# Test Plan

**Version:** 1.0 · Công cụ: pytest (+respx, pytest-asyncio), vitest, Playwright, Remotion render test
Nguyên tắc: **unit test không cần GPU/API key/network** — mọi provider có mock adapter; integration test chạy với docker-compose test profile.

---

# 1. Tầng test & phạm vi bắt buộc

## 1.1 Unit (pytest / vitest) — chạy mỗi commit, < 3 phút

| Khu vực | Case bắt buộc |
|---|---|
| **Provider router (FR-21)** | chain đúng thứ tự; skip provider thiếu key; skip paid khi `ALLOW_PAID=false`; failover khi ProviderError(retryable); xoay key khi QuotaError; hết chain → AllProvidersFailed; ghi usage đúng |
| **State machine (FR-17)** | toàn bộ ma trận chuyển hợp lệ/không hợp lệ (test parametrize từng cạnh); FAILED → resume đúng trạng thái trước; ghi status_history |
| **Scene validator** | từng rule §5 scene-json-schema.md (ràng buộc layout, duration vs audio, hex màu, asset license, tổng duration); auto-fix khi AI sinh vs 422 khi user save |
| **Fact-check verdict** | tổng hợp verdict project từ claims (FAIL > WARN > PASS); override của human |
| **Versioning** | tạo version tăng dần; parent_version đúng; restore → đánh stale các step sau; diff scene-level (added/removed/changed theo scene_id) |
| **Cache key** | canonical JSON ổn định (đổi thứ tự key/scene_number không đổi hash; đổi content đổi hash) |
| **Cost cap** | vượt DAILY_COST_CAP → pause + event |
| **Zod schema (FE)** | parse fixture Scene JSON hợp lệ/không hợp lệ — cùng fixtures với pytest (share thư mục `packages/remotion-templates/schema/fixtures/`) |

## 1.2 Integration (pytest + compose test profile) — mỗi PR, < 10 phút

* **Pipeline end-to-end với MockLLM**: topic → research (nguồn từ fixture HTML) → factcheck → outline → script → storyboard → scene_set; assert: mỗi bước tạo step_version, state machine đi đúng đường, scene JSON pass validator.
* MockLLM = adapter `mock` trả câu trả lời từ fixture theo prompt name — deterministic, không network.
* **Human gate**: run dừng ở NEED_REVIEW; approve qua API → chạy tiếp; restore version → stale.
* **TTS integration**: edge-tts thật (đánh dấu `@pytest.mark.external`, chạy nightly không chạy mỗi PR) + mock cho PR.
* **DB**: migration lên/xuống sạch trên DB rỗng; seed idempotent.
* **NATS (Phase 2+)**: publish request → consumer xử lý → done; redeliver khi không ack; DLQ sau max_deliver; dedupe theo event_id.

## 1.3 Render test (render-worker) — mỗi PR đổi template/schema

* Render fixture scene mỗi layout × 2 format ra MP4; assert: exit 0, duration khớp ±100ms, resolution đúng, file > 0 byte.
* Visual regression (Phase 2): screenshot frame giữa scene, so sánh pixel diff < 2% với baseline commit.

## 1.4 E2E (Playwright) — nightly + trước release

Kịch bản chuẩn (map với api-spec §11): đăng nhập → tạo project → chạy research (MockLLM qua env test) → pin nguồn → approve → … → edit 1 scene trong editor → preview Player hiển thị → render → download MP4. Assert từng màn theo acceptance criteria trong backlog.

## 1.5 Prompt eval — trước khi activate prompt version mới (thủ công có công cụ)

* Bộ 10 topic cố định `backend/tests/fixtures/eval_topics.json`.
* `make prompt-eval PROMPT=script.generate V=3` → chạy 10 topic với LLM thật, xuất bảng so sánh version cũ/mới (độ dài, giữ số liệu, parse JSON ok).
* Người duyệt (BA/owner) chấm đạt/không trước khi activate — ghi kết quả vào PR.

---

# 2. Coverage gate & CI

| Pipeline CI (GitHub Actions / tương đương) | Điều kiện merge |
|---|---|
| lint (ruff, eslint, mypy) | pass |
| unit backend + frontend | pass, coverage `app/services` + `app/adapters` ≥ 80% |
| scene schema sync | `make gen-scene-schema` không tạo diff |
| integration (compose test) | pass |
| render smoke (1 layout × 1 format) | pass |
| E2E | nightly — fail tạo issue tự động, không chặn PR |

---

# 3. Test data & môi trường

* Fixtures: HTML bài viết mẫu (5 nguồn khác provider), Scene JSON mỗi layout (hợp lệ + 3 biến thể lỗi), eval topics, ảnh mẫu license CC0.
* Compose test profile: postgres tmpfs, minio, **không** ollama (MockLLM), **không** network ngoài (chặn egress trong CI để bắt test lén gọi API thật).
* Secrets test: `JWT_SECRET=test`, `FERNET_MASTER_KEY` cố định — không dùng key thật trong CI.

# 4. Định nghĩa Done (test) cho mỗi story

Story chỉ được đóng khi: (1) unit test cho logic mới, (2) integration nếu chạm pipeline/DB, (3) cập nhật fixture nếu đổi contract, (4) CI xanh, (5) acceptance criteria trong story được verify (ghi cách verify vào PR).
