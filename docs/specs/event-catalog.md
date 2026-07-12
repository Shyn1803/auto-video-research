# Event Catalog (NATS JetStream)

**Version:** 1.0 · Áp dụng từ Phase 2 · Đi kèm [ARCHITECTURE.md](../ARCHITECTURE.md) §3
Pydantic models: `backend/app/events/` — tài liệu này là spec, code là nguồn chân lý sau khi implement (CI kiểm tra đồng bộ bằng export JSON Schema).

## Envelope chung (mọi event)

```json
{
  "event_id": "uuid",              // Nats-Msg-Id — JetStream dedupe window 10 phút
  "event_type": "render.scene.request",
  "schema_version": "1.0.0",
  "occurred_at": "2026-07-10T00:00:00Z",
  "correlation_id": "uuid",        // = run_id hoặc render_batch_id, xuyên suốt 1 pipeline run
  "payload": { }
}
```

Quy tắc consumer: idempotent (kiểm tra trạng thái đích trước khi xử lý); ack sau khi hoàn tất; `max_deliver=5`, quá → publish sang `{subject}.dlq`.

---

## Stream `RENDER` (WorkQueue)

### `render.scene.request` — Pipeline → Render Worker

```json
"payload": {
  "render_id": "uuid", "project_id": "uuid", "scene_id": "uuid",
  "scene_json": { },                 // Scene JSON đầy đủ (đã produce audio)
  "format": "vertical_1080x1920",
  "template_package_version": "1.2.0",
  "cache_key": "sha256..."
}
```

### `render.scene.done` — Render Worker → Pipeline

```json
"payload": { "render_id": "uuid", "status": "done|failed|cache_hit",
             "output_path": "renders/{project}/{cache_key}.mp4",
             "duration_ms": 8214, "error": null, "worker_id": "render-worker-2" }
```

### `render.video.request` / `render.video.done` — job merge

```json
"payload": { "render_id": "uuid", "project_id": "uuid", "format": "...",
             "scene_outputs": ["renders/.../a.mp4", "..."],   // đúng thứ tự
             "bgm": { "storage_path": "...", "volume": 0.12, "fade_out_ms": 2000 },
             "output_path": "videos/{project}/{version}/{format}.mp4" }
```

## Stream `MEDIA` (WorkQueue)

### `tts.request` / `tts.done` — Pipeline → Voice Worker

```json
// request
"payload": { "job_id": "uuid", "project_id": "uuid", "scene_id": "uuid",
             "text": "…tiếng Việt…", "voice_id": "female_default", "speed": 1.0,
             "cache_key": "sha256(text+voice+speed+engine)" }
// done
"payload": { "job_id": "uuid", "status": "done|failed",
             "audio_path": "audio/{project}/{hash}.mp3", "duration_ms": 4820,
             "timestamps": [{"word": "Xin", "start_ms": 0, "end_ms": 210}],
             "engine_used": "edge_tts", "error": null }
```

### `asset.request` / `asset.done` — Pipeline → Asset Worker

```json
// request
"payload": { "job_id": "uuid", "project_id": "uuid", "scene_id": "uuid",
             "query_vi": "chip GPU trung tâm dữ liệu",
             "media_type": "image", "orientation": "vertical",
             "allow_generation": true }
// done
"payload": { "job_id": "uuid", "status": "done|failed",
             "asset_id": "uuid", "provider": "pexels", "license": "Pexels License",
             "storage_path": "assets/{hash}.jpg", "error": null }
```

## Stream `PUBLISH` (WorkQueue)

### `publish.request` / `publish.done`

```json
// request
"payload": { "publish_id": "uuid", "project_id": "uuid", "platform": "youtube",
             "video_path": "videos/...", "title": "...", "description": "...",
             "tags": ["AI"], "ai_disclosed": true }
// done
"payload": { "publish_id": "uuid", "status": "published|failed",
             "external_id": "dQw4...", "external_url": "https://youtu.be/...", "error": null }
```

## Stream `EVENTS` (Limits, retention 7 ngày — cho UI/monitoring, không điều khiển luồng)

| Subject | Payload |
|---|---|
| `project.status` | `{project_id, from, to, actor, reason}` |
| `step.progress` | `{project_id, run_id, step, pct, message}` |
| `render.progress` | `{project_id, batch_id, done, total, current_scene_number}` |
| `provider.failover` | `{capability, from_provider, to_provider, reason}` |
| `provider.exhausted` | `{provider, api_key_label, exhausted_until}` |
| `cost.cap_reached` | `{cap_usd, spent_usd, action: "pipeline_paused"}` |
| `factcheck.verdict` | `{project_id, overall_verdict, fail_claims: int, warn_claims: int}` |

## Versioning event

Cùng quy tắc semver như Scene JSON: thêm field optional = minor; đổi/xoá field = major + consumer hỗ trợ song song 2 major trong 1 release chuyển tiếp.
