# API Specification

**Version:** 1.0 · Base URL: `/api/v1` · FastAPI (OpenAPI tự sinh tại `/docs` khi chạy — tài liệu này là bản thiết kế để FE/BE làm song song)
**Đi kèm:** [database-schema.md](database-schema.md) · [scene-json-schema.md](scene-json-schema.md)

## Quy ước chung

* **Auth:** `Authorization: Bearer <access_token>` (JWT, 15 phút) — trừ nhóm `/auth`. Refresh qua cookie httpOnly.
* **Phân quyền:** 🅐 = admin only; 🅞 = owner của project hoặc admin; còn lại = mọi user đã đăng nhập.
* **Error format** (mọi lỗi):

```json
{ "error": { "code": "SCENE_VALIDATION_FAILED", "message": "texts vượt giới hạn layout MediaFull",
             "details": [{ "field": "texts", "rule": "max_items", "limit": 2 }] } }
```

* Codes chuẩn: `400 VALIDATION`, `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `404 NOT_FOUND`, `409 CONFLICT` (sai state machine), `422 SCHEMA_INVALID`, `429 RATE_LIMITED`, `503 PROVIDER_UNAVAILABLE` (hết chain FR-21).
* **Phân trang:** `?page=1&size=20` → `{ "items": [...], "total": 134, "page": 1, "size": 20 }`.
* **Idempotency:** POST tạo tài nguyên nhận header `Idempotency-Key` (optional).

---

# 1. Auth

| Method | Path | Body → Response | Ghi chú |
|---|---|---|---|
| POST | `/auth/login` | `{email, password}` → `{access_token, must_change_password, user}` + set refresh cookie | 429 sau 5 lần sai/15' |
| POST | `/auth/refresh` | (cookie) → `{access_token}` | rotate refresh token |
| POST | `/auth/logout` | → 204 | revoke refresh |
| POST | `/auth/change-password` | `{old_password, new_password}` → `{detail}` | clears must_change_password flag |
| GET | `/auth/me` | → `{id, email, display_name, role}` | |
| 🅐 POST | `/users` | `{email, password, display_name, role}` → User | |
| 🅐 GET/PATCH | `/users`, `/users/{id}` | | deactivate qua PATCH `is_active` |

---

# 2. Projects (FR-01, FR-17)

| Method | Path | Mô tả |
|---|---|---|
| GET | `/projects` | List (filter: `status`, `mode`, `q`; sort `updated_at`) — user thường chỉ thấy project mình |
| POST | `/projects` | `{name, topic, language?, formats?}` → Project (status `DRAFT`) |
| GET 🅞 | `/projects/{id}` | Chi tiết + current version từng step + verdict fact-check tổng |
| GET 🅞 | `/projects/{id}/summary` | (task 5-10) Tóm tắt drawer: metadata + tóm tắt AI + verdict + số cảnh + chi phí "ước tính" (sum llm_usage) + source count + 5 hoạt động gần nhất |
| PATCH 🅞 | `/projects/{id}` | Sửa name/topic/formats (chỉ khi DRAFT/NEED_REVIEW/REVISING) |
| POST 🅞 | `/projects/{id}/clone` | → Project mới (copy version mới nhất mọi step) |
| POST 🅞 | `/projects/{id}/archive` | → 204 |
| DELETE 🅞 | `/projects/{id}` | Chỉ khi DRAFT chưa có dữ liệu; ngược lại 409 → dùng archive |
| GET 🅞 | `/projects/{id}/status-history` | Audit trail |

**Pipeline control (đối thoại chính của Mode 2):**

| Method | Path | Mô tả |
|---|---|---|
| POST 🅞 | `/projects/{id}/steps/{step}/run` | Chạy/regenerate step (`research`\|`outline`\|`script`\|`storyboard`\|`produce`). Async → `{run_id}`; tiến độ qua SSE. 409 nếu state không cho phép |
| POST 🅞 | `/projects/{id}/steps/{step}/approve` | Approve version hiện hành → state machine tiến bước |
| GET 🅞 | `/projects/{id}/runs/{run_id}` | Trạng thái run (fallback khi không dùng SSE) |

---

# 3. Versions (mục 6 SRS) — implemented task 1-5

| Method | Path | Mô tả |
|---|---|---|
| GET 🅞 | `/projects/{id}/steps/{step}/versions` | List `{version, parent_version, stale, created_by, created_at}` |
| GET 🅞 | `/projects/{id}/steps/{step}/current` | Current = max(version) WHERE NOT stale; nếu mọi version stale → max(version) + `all_stale: true` (BR-4) |
| POST 🅞 | `/projects/{id}/steps/{step}/versions` | `{content, parent_version?, actor?}` → **tạo version mới** (insert-only, BR-1; server tự đánh số version); `parent_version` cho phép regenerate-sau-khi-sửa-tay track đúng bản user đã sửa (BR-5) |
| POST 🅞 | `.../versions/{v}/restore` | Đặt v làm hiện hành; các step **sau** đánh dấu stale theo thứ tự (BR-3, không tự đánh dấu chính step vừa restore) → response `{restored, staled_steps: []}`. 404 nếu version không tồn tại; 409 nếu project đang ở trạng thái đang chạy (`RESEARCHING`/`PRODUCING`/`RENDERING`/`PUBLISHING`) |
| GET 🅞 | `.../versions/compare?from=1&to=3` | Diff: text unified diff (`outline`/`script`) hoặc `{type:"scene_set", added[], removed[], changed:[{scene_id, fields[]}]}` (`storyboard`/`scene_set`). 400 nếu `from`/`to` khác step |

**Contract change note (task 1-5):** so với bản trước, endpoint tạo version đổi từ `PUT /versions` (không rõ actor/parent) sang `POST /versions` với body `{content, parent_version?, actor?}` — khớp với BR-5 (regenerate sau sửa tay cần track `parent_version`); thêm endpoint `GET .../current` tách riêng khỏi list (BR-4 cần trả `all_stale`); response `restore` xác nhận field `staled_steps`.

---

# 4. Research & Sources (FR-02)

| Method | Path | Mô tả |
|---|---|---|
| GET 🅞 | `/projects/{id}/sources` | List (filter `pinned`, `disabled`, `trusted`) |
| POST 🅞 | `/projects/{id}/sources` | Thêm tay: `{url}` → server crawl + summarize async |
| PATCH 🅞 | `/projects/{id}/sources/{sid}` | `{pinned?, disabled?}` |
| DELETE 🅞 | `/projects/{id}/sources/{sid}` | |

# 5. Fact Check (FR-04)

| Method | Path | Mô tả |
|---|---|---|
| GET 🅞 | `/projects/{id}/claims` | `[{id, claim_text, claim_type, verdict, evidence:[{source_id, quote, supports}]}]` + `overall_verdict` |
| POST 🅞 | `/projects/{id}/claims/{cid}/override` | `{verdict, reason}` — human override, ghi audit (không xoá evidence, BR-3) → response `{claim, overall_verdict, affected_claims: [claim_id]}` (task 4-4, contract change) |
| PATCH 🅞 | `/projects/{id}/sources/{sid}` | `{pinned?, disabled?}` — disable/xoá source kích hoạt tính lại verdict mọi claim có evidence từ nó, đồng bộ cùng response → `{source, overall_verdict, affected_claims: [claim_id]}` (task 4-4 BR-5, contract change — bổ sung so với §4's `{pinned?, disabled?}` gốc) |

Task 4-4 contract change: `override` và source `disable` giờ trả thêm `overall_verdict` (verdict tổng của project sau khi tính lại) và `affected_claims` (danh sách `claim_id` có verdict thay đổi bởi thao tác này) — cả hai tính lại **đồng bộ trong cùng request** (BR-3/BR-5), không phải một job nền riêng.

# 6. Scenes & Storyboard (FR-07/08/09/10)

| Method | Path | Mô tả |
|---|---|---|
| GET 🅞 | `/projects/{id}/scenes?version=latest` | Scene list (đầy đủ Scene JSON), mỗi scene kèm field `approved: bool` (task 5-1) |
| PUT 🅞 | `/projects/{id}/scenes/{scene_id}` | Body = Scene JSON → validate (422 chi tiết, `detail.field_path`) → set dirty, tạo scene_set version mới (autosave debounce phía FE). Sửa một cảnh đã duyệt sẽ tự động bỏ duyệt cảnh đó (task 5-1) |
| POST 🅞 | `/projects/{id}/scenes/{scene_id}/approve` | (task 5-1, FR-09) Duyệt từng cảnh — **không phải theo cả bước** (quyết định đã chốt). `approved` lưu tách khỏi Scene JSON contract (không phải field trong `app/schemas/scene.py`) vì đây là trạng thái workflow UI, không phải nội dung render — xem `app/models/scene_approval.py`. → `{scene_id, approved: true, approved_at}` |
| POST 🅞 | `/projects/{id}/scenes` | `{after_scene_number, layout}` → scene mới từ template rỗng |
| DELETE 🅞 | `/projects/{id}/scenes/{scene_id}` | |
| POST 🅞 | `/projects/{id}/scenes/{scene_id}/duplicate` | |
| POST 🅞 | `/projects/{id}/scenes/reorder` | `{scene_ids: [...]}` thứ tự mới |
| POST 🅞 | `/projects/{id}/scenes/{scene_id}/tts-preview` | Sinh audio 1 scene để nghe thử → `{audio_url, duration_ms}` |
| GET 🅞 | `/projects/{id}/timeline` | `{scenes:[{scene_id, duration_ms, transition}], bgm, total_ms}` |
| PATCH 🅞 | `/projects/{id}/timeline` | Sửa duration/transition/bgm hàng loạt |

# 7. Render (FR-11)

| Method | Path | Mô tả |
|---|---|---|
| POST 🅞 | `/projects/{id}/render` | `{targets?: [{format, platform_profile}]}` → enqueue; `platform_profile` mặc định `generic`; chỉ khi mọi scene approve; → `{render_batch_id}` |
| GET 🅞 | `/projects/{id}/renders` | Trạng thái từng job scene/merge (`queued/running/done/failed/cache_hit`, % tổng) |
| POST 🅞 | `/projects/{id}/renders/{rid}/retry` | Retry job failed |
| GET 🅞 | `/projects/{id}/video?format=...&platform_profile=...` | `{url}` presigned MinIO (profile mặc định `generic`; video hoàn chỉnh, 404 nếu chưa READY) |

# 8. Publish & Analytics (FR-12, FR-13)

| Method | Path | Mô tả |
|---|---|---|
| GET 🅞 | `/projects/{id}/publish-preview` | `{title, description, tags, platforms_available}` (theo provider active) |
| POST 🅞 | `/projects/{id}/publish` | `{platform, title?, description?, tags?, scheduled_at?}` → Publish record |
| GET 🅞 | `/projects/{id}/publishes` | Trạng thái từng nền tảng |
| GET | `/analytics/dashboard?from&to&platform` | Tổng hợp metrics |
| GET | `/analytics/videos/{publish_id}` | Metrics theo video theo ngày |
| POST | `/analytics/manual` | `{publish_id, metric, value, metric_date}` — nhập tay |

# 9. Admin

| Method | Path | Mô tả |
|---|---|---|
| 🅐 GET | `/admin/providers` | **Ma trận capability → provider** (active/lý do loại: no_key/health_fail/paid_blocked) — FR-21 |
| 🅐 POST | `/admin/providers/{name}/health-check` | Kiểm tra lại ngay |
| 🅐 CRUD | `/admin/api-keys` | Key trả về dạng masked (`sk-...abc4`); POST validate key trước khi lưu |
| 🅐 CRUD | `/admin/prompts`, `/admin/prompts/{id}/versions` | + POST `/versions/{v}/activate` |
| 🅐 CRUD | `/admin/schedules` | + POST `/schedules/{id}/run-now`; GET `/schedules/{id}/runs` |
| 🅐 GET | `/admin/costs?from&to&group_by=provider\|task\|project` | Cost dashboard data |
| 🅐 GET | `/admin/queue` | NATS: pending/redeliver/DLQ theo stream (Phase 2+) |
| 🅐 POST | `/admin/queue/dlq/{stream}/replay` | Replay DLQ |

# 10. Realtime (SSE)

`GET /events/stream` (auth qua query token 1 lần) — server bridge từ NATS `EVENTS`:

```
event: project.status        data: {project_id, from, to}
event: step.progress         data: {project_id, run_id, step, pct, message}
event: render.progress       data: {project_id, batch_id, done, total, current_scene}
event: provider.failover     data: {capability, from_provider, to_provider}
event: cost.cap_reached      data: {cap, spent}
```

FE filter theo project đang mở. Fallback: polling GET `/projects/{id}/runs/{run_id}`.

---

# 11. Ví dụ flow Mode 2 (chuỗi call chuẩn — FE dùng làm test scenario)

```
POST /projects                        {name, topic:"GPT-5.5"}
POST /projects/{id}/steps/research/run     → SSE step.progress → NEED_REVIEW
GET  /projects/{id}/sources                → user pin/disable
POST /projects/{id}/steps/research/approve
POST /projects/{id}/steps/outline/run      → review → PUT versions (sửa tay) → approve
POST /projects/{id}/steps/script/run       → review/sửa → approve
POST /projects/{id}/steps/storyboard/run   → sinh storyboard + scene_set
GET  /projects/{id}/scenes                 → edit từng scene (PUT), preview Player
POST /projects/{id}/steps/produce/run      → TTS + asset resolve
POST /projects/{id}/render                 → SSE render.progress → READY
GET  /projects/{id}/video                  → download / POST publish
```
