# Architecture — AI Content Research & Video Automation Platform

**Version:** 1.0 · Đi kèm [SRS.md](SRS.md) v3.0 · Cấu hình provider: [CONFIGURATION.md](CONFIGURATION.md)

---

# 1. Tổng quan

Hệ thống thiết kế theo **modular monolith → tách service theo đo đạc**. Contract giữa các module (Pydantic model / event schema) được chuẩn hoá từ Phase 1 để việc tách ở Phase 2–3 không đổi interface.

## 1.1 Sơ đồ thành phần (Phase 3 — kiến trúc mục tiêu)

```
                        ┌─────────────────────────────┐
                        │  Next.js Frontend            │
                        │  (Remotion Player preview)   │
                        └──────────────┬──────────────┘
                                       │ HTTPS (JWT)
                        ┌──────────────▼──────────────┐
                        │  FastAPI API Gateway         │
                        │  (stateless, scale ngang)    │
                        └──┬───────────┬───────────┬──┘
                           │           │           │
              ┌────────────▼──┐  ┌─────▼─────┐  ┌──▼───────────┐
              │ Pipeline Svc  │  │ Scheduler │  │ Analytics Svc│
              │ (LangGraph)   │  │ Service   │  │              │
              └──────┬────────┘  └─────┬─────┘  └──┬───────────┘
                     │                 │           │
         ┌───────────▼─────────────────▼───────────▼──────────┐
         │              NATS JetStream (Event Bus)             │
         └──┬──────────────┬──────────────┬──────────────┬────┘
            │              │              │              │
   ┌────────▼───┐  ┌───────▼────┐  ┌──────▼─────┐  ┌────▼──────┐
   │ Render     │  │ Voice/TTS  │  │ Asset      │  │ Publisher │
   │ Worker ×N  │  │ Worker ×N  │  │ Worker ×N  │  │ Worker    │
   └────────┬───┘  └───────┬────┘  └──────┬─────┘  └────┬──────┘
            │              │              │              │
   ┌────────▼──────────────▼──────────────▼──────────────▼────┐
   │  PostgreSQL (+pgvector)   │   MinIO / S3   │  Ollama /   │
   │  state, versions, usage   │   assets, mp4  │  local AI   │
   └───────────────────────────────────────────────────────────┘
```

## 1.2 Phase mapping

| Thành phần | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| API + Pipeline + Scheduler | 1 process FastAPI | 1 process | Tách Pipeline/Scheduler nếu nghẽn |
| Render Worker | Module trong process (subprocess Remotion) | **Tách process, NATS queue** | Pool scale ngang |
| Voice/Asset Worker | Module | Tách cùng Render hoặc riêng | Pool scale ngang |
| Publisher/Analytics | Module | Module | Tách nếu cần |
| NATS JetStream | Chưa dùng | **Bật** | Cluster 3 node |
| Deployment | docker-compose | docker-compose (nhiều host được) | Cân nhắc k8s theo tải |

---

# 2. Pipeline (LangGraph)

## 2.1 Graph

```
research → fact_check → write(outline→script) → storyboard → produce → render → publish
   │            │              │                    │            │
   └── mỗi node: checkpoint PostgreSQL, retry có backoff, human-gate (Mode 2)

Node storyboard nội bộ là pipeline tầng (specs/layout-engine.md):
  [AI] Semantic Storyboard (nội dung + ý đồ, KHÔNG layout)
   → Scene Tree → Semantic Analysis → Layout Classifier (rule table)
   → Constraint Resolver (preset flex) → Responsive Solver (16:9/9:16)
   → Theme Engine → Motion Engine → Scene JSON (resolved)
  Tầng sau AI là pure function — đổi format/theme/layout không gọi lại LLM.
```

* **Human gate**: Mode 2 dừng ở mỗi node chờ approve (LangGraph interrupt); Mode 1 chạy thẳng trừ gate Fact Check.
* **Checkpoint**: `langgraph-checkpoint-postgres` — resume đúng node sau crash; state là Pydantic model serialize JSONB.
* **Node = module có interface chuẩn**: `run(input: NodeInput, ctx: RunContext) -> NodeOutput`. Đây là contract để tách node thành consumer NATS ở Phase 2–3 (NodeInput/Output trở thành event payload, không đổi schema).

## 2.2 Task tier & LLM routing

Mỗi lời gọi LLM khai báo `tier` (`cheap` / `strong` / `embedding`). Router đọc chain từ env (xem CONFIGURATION.md), thử từng provider:

```
call(tier, prompt) →
  for provider in chain(tier):
    if not provider.available(): continue      # key missing / health fail / paid khi ALLOW_PAID=false
    try: return provider.call(prompt)          # + ghi llm_usage
    except QuotaError: rotate_key(provider) or next
    except TimeoutError, 5xx: next             # + event provider_failover
  raise AllProvidersFailed                     # → node retry → FAILED nếu hết retry
```

---

# 3. Event Bus (NATS JetStream — Phase 2+)

## 3.1 Subjects & streams

| Stream | Subject | Producer → Consumer | Retention |
|---|---|---|---|
| `RENDER` | `render.scene.request` / `render.scene.done` | Pipeline → Render Worker | WorkQueue |
| `RENDER` | `render.video.request` / `render.video.done` | Pipeline → Render Worker | WorkQueue |
| `MEDIA` | `tts.request` / `tts.done` | Pipeline → Voice Worker | WorkQueue |
| `MEDIA` | `asset.request` / `asset.done` | Pipeline → Asset Worker | WorkQueue |
| `PUBLISH` | `publish.request` / `publish.done` | Scheduler/UI → Publisher | WorkQueue |
| `EVENTS` | `project.status.*`, `provider.failover`, `cost.cap_reached` | mọi service → Monitoring/UI (SSE) | Limits (7d) |

## 3.2 Quy tắc

* Mọi event có `event_id` (UUID) + `Nats-Msg-Id` → JetStream dedupe; consumer idempotent (kiểm tra trạng thái đích trước khi xử lý).
* Ack sau khi hoàn tất; `max_deliver` + DLQ subject (`*.dlq`) cho message lỗi lặp — Admin xem và replay từ UI.
* Payload là Pydantic schema có `schema_version` — cùng quy tắc semver như Scene JSON.

---

# 4. Render Worker

* Mỗi worker: Node.js + Remotion CLI, nhận `render.scene.request` (scene JSON + template id + format), render ra MinIO, ack + phát `render.scene.done`.
* **Cache**: key = `hash(scene_json + template_version + format)`; hit → trả URL luôn, không render.
* **Merge**: node render cuối ghép scene (ffmpeg concat) + merge audio + encode (h264, CRF cấu hình).
* **Scale**: số worker = biến compose `RENDER_WORKER_REPLICAS`; Phase 3 autoscale theo queue depth (NATS consumer pending).
* **Đa format**: cùng Scene JSON render 9:16 và 16:9 — template chịu trách nhiệm layout responsive; job format khác nhau là job độc lập (cache riêng).
* Worker stateless: crash → message redeliver sang worker khác.

---

# 5. Data Model (bảng chính)

```
users(id, email, role, ...)
projects(id, owner_id, name, topic, status, language, formats[], created_at, updated_at)
status_history(project_id, from_status, to_status, actor, reason, at)
step_versions(id, project_id, step, version, parent_version, content_jsonb, stale, created_by, created_at)
sources(id, project_id, url, title, author, published_at, summary, content_hash,
        partial_content, pinned, disabled, license)
claims(id, project_id, text, verdict, sources[])          -- fact check theo claim
scenes(id, project_id, storyboard_version, scene_number, scene_json jsonb,
       schema_version, content_hash, dirty)
assets(id, provider, source_url, license, attribution_required, content_hash, minio_path)
renders(id, project_id, scene_id?, format, status, cache_key, output_path, worker_id, duration_ms)
publishes(id, project_id, platform, status, external_id, scheduled_at, published_at, error)
metrics(video_id, platform, metric, value, date, source)
prompts(id, name, version, template, variables[], active)
api_keys(id, provider, key_encrypted, status, usage_count, quota_remaining)
llm_usage(id, provider, model, tokens_in, tokens_out, cost_estimate, task, project_id, created_at)
schedules(id, type, cron, enabled, config_jsonb)
schedule_runs(schedule_id, started_at, finished_at, status, error, cost)
embeddings: pgvector trên sources/documents (dedupe + RAG)
```

* Partition theo tháng: `llm_usage`, `schedule_runs`, `metrics` (khối lượng lớn theo thời gian).
* JSONB cho nội dung version — tránh schema migration mỗi khi content đổi cấu trúc; schema thực thi ở tầng Pydantic.

---

# 6. Storage layout (MinIO / S3)

```
assets/{content_hash}.{ext}          # dedupe theo hash
audio/{project}/{scene_hash}.mp3     # TTS cache
renders/{project}/{cache_key}.mp4    # scene render cache
videos/{project}/{version}/{format}.mp4
```

* Bucket versioning bật cho `videos/`. Lifecycle rule dọn `renders/` cache > 30 ngày.
* Adapter chung MinIO/S3 — đổi bằng env (`STORAGE_PROVIDER`), path không đổi.

---

# 7. Frontend

* Next.js (App Router), shadcn/ui; state server qua React Query.
* **Preview**: Remotion Player import cùng bộ template composition mà Render Worker dùng (monorepo share package `@app/remotion-templates`) — preview và render **cùng một code**, không lệch.
* Realtime: SSE từ API (bridge từ NATS `EVENTS`) cho tiến độ pipeline/render.
* Editor Scene: form sinh từ JSON Schema (schema-driven UI) — schema đổi thì form theo kịp.

---

# 8. Security

* JWT access (15') + refresh (7d, rotate); RBAC middleware theo route.
* Secrets: env / Docker secrets; API key user-provided mã hoá Fernet trong DB, master key qua env (KMS khi lên cloud).
* Rate limit: theo user + IP (slowapi / nginx). CORS allowlist.
* Audit: `status_history`, api_key usage, admin action log.
* Network: chỉ API và Frontend expose; NATS/PostgreSQL/MinIO/Ollama trong network nội bộ docker.

---

# 9. Observability

| Lớp | Công cụ (self-host, free) |
|---|---|
| Metrics API/worker | Prometheus + Grafana (FastAPI instrumentator, NATS exporter) |
| LLM traces (prompt, token, latency, version) | Langfuse self-host |
| Errors | Sentry self-host / GlitchTip |
| Cost | `llm_usage` → Grafana dashboard + alert `DAILY_COST_CAP` |
| Queue | NATS monitoring endpoint → Grafana (pending, redeliver, DLQ) |

Alert tối thiểu: pipeline FAILED, DLQ có message, cost cap, worker down, disk MinIO > 80%.

---

# 10. Deployment

## Phase 1–2: docker-compose

```
services: frontend, api, render-worker (replicas), voice-worker,
          postgres, nats, minio, ollama, searxng,
          prometheus, grafana, langfuse
```

* 1 host GPU (Ollama, TTS local, SD) + có thể thêm host CPU cho render worker.
* `.env` quyết định toàn bộ provider (CONFIGURATION.md); cùng compose file cho dev/prod, khác env.

## Phase 3: scale

* Tuỳ chọn A (đơn giản, ưu tiên): nhiều host docker-compose, NATS cluster 3 node, worker join qua NATS URL — không cần k8s.
* Tuỳ chọn B (tải lớn): Kubernetes + KEDA autoscale worker theo NATS queue depth.
* PostgreSQL: pgbouncer; đọc nặng → read replica. Backup: daily dump + WAL archive; MinIO replicate sang host 2.

---

# 11. Quyết định kiến trúc (ADR tóm tắt)

| # | Quyết định | Lý do | Đánh đổi |
|---|---|---|---|
| 1 | Modular monolith trước, tách theo đo đạc | Tốc độ phát triển, ít hạ tầng khi chưa có tải | Phải giữ kỷ luật contract giữa module |
| 2 | LangGraph checkpoint thay vì tự viết saga | Resume/retry/human-gate có sẵn, khớp Postgres | Gắn với hệ sinh thái LangChain |
| 3 | NATS JetStream thay Kafka/RabbitMQ | Nhẹ, 1 binary, WorkQueue + dedupe đủ nhu cầu | Ecosystem nhỏ hơn Kafka |
| 4 | Scene JSON + schema_version là contract trung tâm | Preview/render/cache/versioning đều dựa vào nó | Đầu tư thiết kế schema từ sớm |
| 5 | Provider adapter + env chain (local-first) | Chạy 0đ, kích hoạt paid không sửa code, chống lock-in | Mỗi capability phải viết ≥ 2 adapter |
| 6 | Remotion Player share template với worker | Preview = render, không lệch pixel | Monorepo JS/TS bên cạnh Python |
| 7 | JSONB cho version content | Nội dung đổi cấu trúc thường xuyên | Query sâu vào content chậm hơn cột thường |
| 8 | **Layout Engine tầng (Gamma-style): AI chỉ sinh semantic, classifier + constraint preset quyết bố cục** | Cô lập LLM khỏi quyết định layout (deterministic, test được); đổi format/theme không tốn token; thêm layout class không đổi engine | v1 dùng preset flex theo class thay vì solver tổng quát — solver (component tự khai constraints) là v1.1 khi cần >~15 class/variants |
