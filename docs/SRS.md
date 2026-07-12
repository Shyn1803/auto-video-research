# Software Requirements Specification (SRS)

# AI Content Research & Video Automation Platform

**Version:** 3.0
**Ngày cập nhật:** 2026-07-10
**Bộ tài liệu:** [SRS.md](SRS.md) (tài liệu này) · [ARCHITECTURE.md](ARCHITECTURE.md) (kiến trúc & scale) · [CONFIGURATION.md](CONFIGURATION.md) (env & provider)

**Thay đổi so với v2.0:**
- Phạm vi là **hệ thống production đầy đủ**, chia theo Phase triển khai — không cắt scope ở mức MVP. Mọi FR đều là cam kết, Phase chỉ quyết định thứ tự.
- Bổ sung **FR-21 Provider Configuration**: mọi năng lực bên ngoài (LLM, TTS, search, asset, publish, storage) hoạt động theo nguyên tắc **local-first qua env**; provider trả phí tự kích hoạt khi API key được cung cấp, không sửa code.
- Kiến trúc mục tiêu khôi phục đầy đủ multi-agent trên NATS JetStream (xem ARCHITECTURE.md), triển khai theo lộ trình modular monolith → tách service.

---

# 1. Giới thiệu

## 1.1 Mục tiêu

Xây dựng nền tảng Web AI — một **AI Video Production Studio** — tự động nghiên cứu thông tin, tổng hợp nội dung, tạo storyboard, dựng video bằng Remotion và xuất bản lên các nền tảng mạng xã hội. AI hỗ trợ toàn bộ quy trình từ nghiên cứu đến xuất bản; người dùng tham gia chỉnh sửa ở bất kỳ bước nào.

Mục tiêu chính:

* Tự động nghiên cứu thông tin từ nhiều nguồn (ưu tiên API/RSS chính thức).
* Hạn chế hallucination qua Fact Checking định lượng (PASS / WARN / FAIL) theo từng claim.
* Sinh nội dung **tiếng Việt** có dẫn nguồn.
* Chuyển nội dung thành Storyboard và Scene JSON (schema có version).
* Preview từng Scene tức thì (Remotion Player); chỉ render sau khi người dùng xác nhận.
* Versioning toàn bộ dữ liệu với quan hệ parent giữa các bước.
* Vận hành nhiều Project song song, scale ngang render worker và AI worker.
* **Kiểm soát chi phí bằng thiết kế**: local-first, provider trả phí kích hoạt qua env, cost tracking + cap theo ngày.

## 1.2 Nguyên tắc Provider (xuyên suốt hệ thống)

Mọi năng lực phụ thuộc bên ngoài đều nằm sau **Adapter interface** và được chọn bằng biến môi trường:

1. **Local-first mặc định**: không có API key nào → hệ thống vẫn chạy đầy đủ pipeline bằng công cụ local/self-host (Ollama, BGE-M3, edge-tts/viXTTS, SearXNG, Stable Diffusion, MinIO).
2. **Kích hoạt bằng key**: cung cấp API key qua env (hoặc FR-15 API Key Management) → provider tương ứng tự động tham gia chuỗi ưu tiên, không sửa code, không deploy lại.
3. **Fallback chain**: mỗi capability khai báo chuỗi ưu tiên (ví dụ `LLM_CHAIN=ollama,gemini,openrouter`); provider lỗi/hết quota → tự chuyển provider kế tiếp + ghi log.

Đặc tả chi tiết biến env và ma trận provider: xem [CONFIGURATION.md](CONFIGURATION.md).

---

# 2. Phạm vi

Hệ thống gồm hai chế độ hoạt động. **Cả hai đều thuộc phạm vi cam kết**; thứ tự triển khai theo Phase (mục 11).

## Mode 1 — Daily AI News (Full-Auto có gate)

Hệ thống tự chạy theo Scheduler (ví dụ 07:00 mỗi sáng):

Research → Ranking → Fact Check (gate) → Outline → Script → Storyboard → Scene JSON → Render → Publish

**Gate publish (cấu hình được qua env `MODE1_AUTOPUBLISH`):**

* `off` (mặc định khi mới vận hành): mọi video dừng ở `READY`, chờ duyệt 1 click.
* `pass_only`: chỉ auto-publish khi Fact Check = `PASS`; `WARN` dừng chờ duyệt; `FAIL` dừng pipeline + thông báo.
* `on`: auto-publish PASS và WARN (chỉ khuyến nghị khi tỉ lệ chính xác thống kê ≥ ngưỡng cấu hình, mặc định 95% qua 30 ngày — hệ thống hiển thị chỉ số này trên dashboard để Admin quyết định).

## Mode 2 — Interactive Project

Người dùng nhập chủ đề (ví dụ: GPT-5.5, MCP, AI Agent, LangGraph, Gemma, OCR, Llama). Workflow chia nhiều bước; người dùng có quyền: xem kết quả, chỉnh sửa, approve, quay lại bước trước, lưu version, tiếp tục sau.

---

# 3. Personas

## Admin

* Quản lý người dùng, phân quyền (RBAC).
* Quản lý Prompt (FR-14), Scheduler (FR-16), API Keys & provider activation (FR-15, FR-21).
* Theo dõi Render Queue, Worker Health, chi phí, audit log.

## Content Creator

* Tạo Project, Research, viết Script, chỉnh sửa Storyboard/Scene, Render, Publish, xem Analytics.

---

# 4. Functional Requirements

## FR-01 Project Management

Tạo, sửa, xoá, clone, archive Project. Mỗi Project có: Name, Topic, Status (state machine FR-17), Created/Updated Date, Owner, ngôn ngữ nội dung (mặc định `vi`), format video đích.

Danh sách Project hỗ trợ filter theo status/owner/ngày, phân trang, tìm kiếm.

## FR-02 Research

Người dùng nhập Topic. AI tự động: search đa nguồn, thu thập bài viết, tổng hợp, dedupe (URL hash + similarity embedding), tóm tắt tiếng Việt.

**Chiến lược nguồn (ưu tiên API/RSS chính thức):**

| Nguồn | Phương thức | Chi phí |
|---|---|---|
| arXiv | arXiv API | Free |
| Hacker News | Algolia HN API | Free |
| GitHub | GitHub API | Free |
| Blog OpenAI / Anthropic / Google / DeepMind / NVIDIA / HuggingFace | RSS | Free |
| Reddit | RSS công khai của subreddit | Free |
| Papers with Code | API/RSS | Free |
| Web search | Chuỗi provider: SearXNG self-host → Tavily → Brave → SerpAPI (env-activated) | Free → trả phí |
| Crawl HTML | trafilatura / crawl4ai | Free |

**Ràng buộc:** tôn trọng robots.txt/ToS; cache bài đã crawl (không request lặp); nguồn paywall chỉ lấy title+abstract và đánh dấu `partial_content`; mọi document lưu kèm ngày thu thập và hash nội dung.

Output: danh sách nguồn (tóm tắt, link, ngày, tác giả). Người dùng: thêm/xoá/pin/disable nguồn. Nguồn pinned luôn được đưa vào context các bước sau.

## FR-03 Ranking

AI đánh giá: độ mới, độ phổ biến, độ tin cậy (theo danh sách nguồn tin cậy cấu hình được), số nguồn xác nhận, mức độ liên quan. Output: Score + Reason (tiếng Việt). Trọng số các tiêu chí cấu hình được ở cấp hệ thống.

Task tier: `cheap` → mặc định chạy LLM local (FR-18).

## FR-04 Fact Checking

Trích xuất claim quan trọng (tên model, benchmark, release date, paper, github, phiên bản) và kiểm tra chéo giữa các nguồn.

**Tiêu chí định lượng:**

* `PASS`: mọi claim quan trọng có ≥ 2 nguồn độc lập xác nhận.
* `WARN`: claim chỉ 1 nguồn / nguồn ngoài danh sách tin cậy / dựa trên `partial_content`.
* `FAIL`: ≥ 2 nguồn mâu thuẫn về cùng claim → Project chuyển `NEED_REVIEW` + thông báo (email/Telegram, cấu hình env).

Kết quả gắn theo từng claim (claim → nguồn → verdict) và hiển thị trong UI review. Task tier: `strong`.

## FR-05 Outline

AI sinh (tiếng Việt): Hook, Introduction, Problem, Solution, Demo, Conclusion, CTA. Người dùng chỉnh sửa trước khi Generate Script.

## FR-06 Script

AI sinh (tiếng Việt): Title, Description, Tags, Voice Over, Subtitle. Người dùng chỉnh sửa trực tiếp (rich editor, autosave, tạo version mới khi generate lại).

## FR-07 Storyboard — Semantic Storyboard + Layout Engine

Sau khi Script approve, **AI chỉ sinh Semantic Storyboard**: chia cảnh với `purpose` (ý đồ), `narration` (lời đọc) và `components` theo loại nội dung (heading/body/media_intent/stat/bullet/chart_data/table_data/quote/code/group). **AI không quyết định bố cục, vị trí, font, camera, transition hay animation.**

**Layout Engine** (deterministic — [specs/layout-engine.md](specs/layout-engine.md)) đảm nhận phần còn lại: Scene Tree → Semantic Analysis → Layout Classifier (rule table) → Constraint Resolver (preset flex) → Responsive Solver (đa format không gọi lại AI) → Theme → Motion preset → Scene JSON resolved. User ghi đè layout được (`layout_override`).

## FR-08 Scene JSON (Contract render)

Scene JSON là **đầu ra resolved của Layout Engine** và input duy nhất của Remotion.

* Schema định nghĩa bằng **Pydantic** (backend), sinh JSON Schema; frontend/Remotion validate bằng **Zod** từ cùng JSON Schema (một nguồn duy nhất).
* Trường bắt buộc `schema_version` (semver). Package Remotion khai báo range schema hỗ trợ; breaking change → tăng major + migration script.
* Scene lưu kèm `semantic_tree` (nguồn nội dung) + `layout` (kết quả classifier, 11 class PascalCase) + `layout_override`.
* Remotion phía hiện thực: **1 SceneRenderer + primitives + preset json** — không composition cứng per-layout (layout-engine §11).
* Schema v2+: chart line/pie, video nhúng, lower-third, Gallery/Timeline class, karaoke subtitle, constraint solver tổng quát.

## FR-09 Scene Preview & Edit

Preview bằng **Remotion Player trong browser** (không render server-side ở bước này). Người dùng: sửa text/subtitle, đổi layout/ảnh/animation/màu/font, thêm/xoá/duplicate/reorder scene.

Scene thay đổi → chỉ scene đó bị đánh dấu dirty (hash Scene JSON); Final Render chỉ render lại scene dirty.

## FR-10 Timeline

Sau khi approve tất cả Scene: Timeline cho phép kéo dài/rút ngắn scene, đổi transition, đổi BGM (chọn từ thư viện FR-20), preview toàn bộ.

## FR-11 Final Render

Khi bấm Generate Video: Generate Voice (FR-19) → Subtitle → Resolve Assets (FR-20) → Render từng scene (song song trên worker pool) → Encode → Merge Audio → MP4.

* Format hỗ trợ: **9:16 1080×1920** (TikTok/Reels/Shorts) và **16:9 1920×1080** (YouTube). Format khai báo ở cấp Project; một Project có thể render nhiều format từ cùng Scene JSON (layout responsive theo template).
* Render theo scene, cache theo hash Scene JSON — scene không đổi không render lại.
* Job render đưa vào hàng đợi (NATS JetStream), thực thi bởi Render Worker pool scale ngang (chi tiết: ARCHITECTURE.md).

## FR-12 Publish

Publish nằm sau **Publish Adapter**; nền tảng kích hoạt qua env/API key (FR-21):

| Nền tảng | Phương thức | Kích hoạt |
|---|---|---|
| Download | MP4 + Title/Description/Tags copy sẵn | Luôn có |
| YouTube | YouTube Data API (quota free 10.000 units/ngày) | `YOUTUBE_*` credentials |
| TikTok | Content Posting API (cần duyệt app) | `TIKTOK_*` credentials |
| Facebook | Reels/Video API (cần duyệt app) | `FACEBOOK_*` credentials |
| LinkedIn | Video API | `LINKEDIN_*` credentials |

* Có Scheduler đăng theo giờ; retry khi lỗi; trạng thái publish theo dõi được từng nền tảng.
* Video AI-generated bật cờ khai báo "AI-generated content" theo yêu cầu từng nền tảng.
* Nền tảng chưa được cấp API (đang chờ duyệt) → hệ thống tự fallback về Download + hướng dẫn đăng tay.

## FR-13 Analytics

Thu thập: View, Like, Comment, Watch Time, Completion Rate, CTR.

* Provider adapter theo nền tảng: YouTube Analytics API (đầy đủ nhất), TikTok/Facebook API khi được cấp quyền; nền tảng chưa có API → nhập tay qua form.
* Schema thống nhất: `metrics(video_id, platform, metric, value, date, source = api | manual)`.
* Dashboard: theo video, theo kênh, theo thời gian; so sánh giữa các video/chủ đề.
* Job thu thập định kỳ qua Scheduler (FR-16).

## FR-14 Prompt Management

* Prompt lưu DB, có version; mỗi Agent/node trỏ `prompt_id + version`.
* Admin: sửa, so sánh version, rollback, A/B hai version prompt trên cùng task — không deploy lại.
* Prompt có biến template (topic, ngôn ngữ, độ dài...) validate trước khi lưu.

## FR-15 API Key & Provider Management

* Bảng `api_keys` mã hoá (Fernet/KMS): key gắn provider, usage counter, quota còn lại, trạng thái (active/exhausted/revoked).
* Hỗ trợ **nhiều key cùng provider** để xoay vòng quota; router tự chuyển key khi hết quota.
* Key nhập qua UI Admin **hoặc** env (env override DB — phục vụ deploy tự động). Audit log mọi lần dùng.
* UI hiển thị provider nào đang active theo capability (LLM/TTS/Search/Publish/...) — phản chiếu trực tiếp cấu hình FR-21.

## FR-16 Scheduler Management

* Phase 1: APScheduler trong API service. Phase 3: scheduler tách riêng, job phát qua NATS (đảm bảo chỉ chạy 1 lần khi có nhiều instance — leader election / JetStream dedupe).
* Admin: bật/tắt schedule, đổi cron, xem lịch sử run (thành công/thất bại/lý do/chi phí), chạy thủ công (run now).
* Loại job: Mode 1 pipeline, thu thập analytics, dọn cache, publish theo giờ.

## FR-17 Project State Machine

```
DRAFT → RESEARCHING → NEED_REVIEW ⇄ REVISING → APPROVED
      → PRODUCING → RENDERING → READY → PUBLISHING → PUBLISHED
Mọi trạng thái → FAILED (resume về trạng thái trước đó)
ARCHIVED (từ mọi trạng thái kết thúc)
```

* Cột `status` + bảng `status_history(project_id, from, to, actor, reason, at)` — kiêm audit log.
* Resume sau lỗi: LangGraph checkpoint (PostgreSQL) cho pipeline; job render idempotent theo scene hash.

## FR-18 LLM Routing & Cost Control

**Routing theo task tier (mapping tier → chain cấu hình qua env, xem CONFIGURATION.md):**

| Tier | Task | Chain mặc định |
|---|---|---|
| `cheap` | tóm tắt, dedupe, ranking, trích claim | ollama → gemini-flash → openrouter:free |
| `strong` | fact check, outline, script, storyboard | gemini → groq → openrouter:free → openrouter:paid* |
| `embedding` | vector hoá | bge-m3 local → gemini-embedding* |

\* chỉ tham gia chain khi có API key và `ALLOW_PAID=true`.

**Cost control:**

* Bảng `llm_usage(provider, model, tokens_in, tokens_out, cost_estimate, task, project_id, created_at)` ghi mọi call.
* `DAILY_COST_CAP` (env): vượt ngưỡng → pipeline pause + thông báo Admin; Mode 2 hiển thị cảnh báo cho user.
* Dashboard chi phí: theo ngày/provider/task/project.

## FR-19 Voice / TTS tiếng Việt

TTS Adapter, chain cấu hình qua env:

| Ưu tiên mặc định | Engine | Kích hoạt | Ghi chú |
|---|---|---|---|
| 1 | edge-tts (`vi-VN-HoaiMyNeural`, `vi-VN-NamMinhNeural`) | Luôn có (free) | Word-level timestamp → subtitle sync |
| 2 | viXTTS / XTTS-v2 fine-tune Việt (local GPU) | `TTS_LOCAL_MODEL` | Clone giọng |
| 3 | F5-TTS checkpoint tiếng Việt (local) | `TTS_LOCAL_MODEL` | Tự nhiên hơn XTTS |
| Khi có key | FPT.AI TTS / Zalo AI / Google Cloud TTS vi-VN | `FPT_API_KEY` v.v. | Chất lượng cao nhất, tự lên đầu chain nếu cấu hình |

* Chức năng: chọn giọng nam/nữ, tốc độ, pitch, preview audio từng scene trước render, cache audio theo hash (text + voice + params).
* Subtitle timestamp: từ engine nếu có; fallback align bằng faster-whisper / PhoWhisper (local).

## FR-20 Asset Management & Licensing

* Nguồn: Pexels → Pixabay → Unsplash (API key free, env-activated); icon Lucide/Tabler (MIT); ảnh AI local (Stable Diffusion / FLUX.1-schnell) hoặc API sinh ảnh khi có key; BGM từ Pixabay Music/YouTube Audio Library.
* **Bắt buộc:** mỗi asset lưu `source_url, license, attribution_required, provider`; từ chối asset không rõ license.
* Asset lưu MinIO (hoặc S3 khi có credentials — cùng adapter), dedupe theo content hash, CDN-ready path.
* Thư viện asset nội bộ: user upload asset riêng (logo, watermark, intro/outro), quản lý theo workspace.

## FR-21 Provider Configuration (env-driven, local-first)

**Yêu cầu trung tâm của hệ thống:**

1. Hệ thống **chạy đầy đủ pipeline với 0 API key** (toàn bộ local/self-host).
2. Mỗi capability có biến env khai báo chain: `LLM_CHAIN`, `TTS_CHAIN`, `SEARCH_CHAIN`, `IMAGE_GEN_CHAIN`, `PUBLISH_PLATFORMS`, `STORAGE_PROVIDER`...
3. Provider chỉ tham gia chain khi điều kiện kích hoạt thoả (API key tồn tại trong env hoặc DB FR-15, service local reachable).
4. Startup: hệ thống kiểm tra từng provider (health check / key validation), log rõ capability nào đang chạy provider nào; UI Admin hiển thị ma trận này.
5. Provider lỗi runtime (timeout, hết quota, 4xx/5xx) → tự chuyển provider kế tiếp trong chain, ghi `provider_failover` event; hết chain → task fail có retry.
6. `ALLOW_PAID=false` (mặc định): mọi provider có cost > 0 bị loại khỏi chain kể cả khi có key — chống phát sinh chi phí ngoài ý muốn.

Danh mục đầy đủ biến env: [CONFIGURATION.md](CONFIGURATION.md).

---

# 5. Workflow

## Mode 1

Scheduler → Research → Ranking → Fact Check (gate) → Outline → Script → Storyboard → Scene JSON → Render → [READY / Publish theo `MODE1_AUTOPUBLISH`]

## Mode 2

Create Project → Research → Review → Outline → Review → Script → Review → Storyboard → Scene JSON → Preview Scene → Edit Scene → Timeline → Preview → Render → Publish

---

# 6. Version Control

* Mỗi bước có version; mỗi version lưu `parent_version` của bước trước.
* Restore bước cũ: các bước sau đánh dấu `stale` (không xoá); UI cảnh báo, user chọn giữ hoặc regenerate.
* Compare: text diff (outline/script); diff theo `scene_id` (storyboard/scene). Visual diff (side-by-side preview 2 version scene) ở Phase 3.
* Lưu trữ: `step_versions(project_id, step, version, parent_version, content_jsonb, created_by, created_at)`.
* Thao tác: Compare, Restore, Duplicate.

---

# 7. AI Agent Architecture

Kiến trúc mục tiêu là **multi-agent trên NATS JetStream** với các agent: Research, Ranking, Fact Check, RAG, Outline, Script, Storyboard, Visual Planning, Asset Retrieval, Voice, Subtitle, Remotion Render, Publisher, Analytics.

**Lộ trình hiện thực (chi tiết: ARCHITECTURE.md):**

* **Phase 1 — Modular monolith**: các agent là module trong 1 codebase FastAPI, orchestrate bằng LangGraph (checkpoint PostgreSQL). Interface mỗi module là Pydantic model — đây chính là contract event sau này.
* **Phase 2 — Tách worker nặng**: Render Worker và Voice/Asset Worker tách process riêng, nhận job qua NATS JetStream; API và pipeline AI vẫn chung service.
* **Phase 3 — Tách agent theo nhu cầu scale**: agent nào nghẽn thì tách thành service riêng consume NATS subject riêng; các agent nhẹ giữ chung service. Event schema đã ổn định từ Phase 1 nên việc tách không đổi contract.

Nguyên tắc: **tách theo đo đạc, không tách trước** — nhưng mọi interface được thiết kế từ đầu để tách được.

---

# 8. Non-functional Requirements

## Performance

* Preview Scene: tức thì (Remotion Player client-side).
* Render lại 1 scene: ≤ 10s trên worker chuẩn (định nghĩa worker chuẩn và số liệu chốt sau benchmark Phase 1 — NFR này review lại mỗi phase).
* Video 60s (9:16, 1080p): ≤ 3 phút trên 1 worker; scale tuyến tính theo số worker (render scene song song).
* Hỗ trợ ≥ 20 Project render đồng thời ở Phase 3 (queue + worker pool).

## Scalability

* API stateless (JWT), scale ngang sau load balancer.
* Render/Voice/Asset worker: scale ngang theo độ dài queue (KEDA/自 script khi chạy k8s; docker-compose scale ở giai đoạn nhỏ).
* PostgreSQL: connection pool (pgbouncer khi cần); dữ liệu lớn (document crawl, usage log) partition theo tháng.
* MinIO → S3-compatible bất kỳ qua cùng adapter.

## Reliability

* Retry có backoff cho mọi call provider; failover theo chain (FR-21).
* Event idempotent (dedupe theo `event_id`, JetStream ack).
* Resume pipeline qua LangGraph checkpoint; render idempotent theo scene hash.
* Backup: PostgreSQL daily dump + WAL; MinIO versioning bucket.

## Security

* JWT Authentication (access + refresh), RBAC (Admin/Creator; mở rộng workspace-level Phase 3).
* API Key encryption at rest (Fernet; KMS khi lên cloud).
* Audit Log (status_history + api key usage + admin actions).
* Rate limiting theo user/IP; CORS allowlist; secret không bao giờ log.

## Monitoring

* API metrics + worker health: Prometheus + Grafana (self-host, free).
* LLM observability (token, latency, prompt version): Langfuse self-host (free) hoặc bảng `llm_usage`.
* Error tracking: Sentry self-host / GlitchTip (free).
* Cost dashboard + daily cap alert.

---

# 9. Technology Stack

| Lớp | Công nghệ | Local-first / kích hoạt |
|---|---|---|
| Frontend | React, Next.js, Tailwind CSS, shadcn/ui, Remotion Player | — |
| Backend | FastAPI, SQLAlchemy, Pydantic | — |
| Workflow | LangGraph (checkpoint PostgreSQL) | — |
| Messaging | NATS JetStream (Phase 2+) | Self-host |
| Database | PostgreSQL + pgvector | Self-host |
| Storage | MinIO ↔ S3 (cùng adapter) | MinIO mặc định; S3 khi có credentials |
| Video | Remotion (kiểm tra company license khi thương mại hoá) | — |
| LLM | Ollama (Qwen2.5) ↔ Gemini/Groq/OpenRouter/Mistral | Local mặc định; cloud khi có key |
| Embedding | BGE-M3 local | Local mặc định |
| TTS | edge-tts / viXTTS / F5-TTS ↔ FPT.AI / Zalo / Google | Free mặc định; paid khi có key |
| Subtitle align | faster-whisper / PhoWhisper | Local |
| Sinh ảnh | Stable Diffusion / FLUX.1-schnell ↔ API khi có key | Local mặc định |
| Search | SearXNG ↔ Tavily / Brave / SerpAPI | Self-host mặc định |
| Crawl | trafilatura / crawl4ai | — |
| OCR | Marker, OpenDataLoader PDF | Local |
| Scheduler | APScheduler → NATS-based (Phase 3) | — |
| Monitoring | Prometheus, Grafana, Langfuse, Sentry/GlitchTip | Self-host |
| Deployment | Docker Compose → Kubernetes (Phase 3, tuỳ tải) | — |

---

# 10. Nguyên tắc thiết kế

* Human-in-the-loop ở các bước quan trọng; mức tự động của Mode 1 là **cấu hình có kiểm soát**, mặc định an toàn (chờ duyệt).
* Storyboard và Scene JSON là nguồn dữ liệu trung tâm, có schema + `schema_version`; Remotion chỉ là Render Engine.
* **AI chỉ sinh nội dung và ý đồ (semantic) — không bao giờ quyết định bố cục/vị trí/font/animation.** Layout Engine deterministic quyết bố cục cuối cùng; đổi format/theme/layout không gọi lại AI (specs/layout-engine.md).
* Mỗi Scene là đơn vị độc lập: preview, cache, render riêng.
* Mọi dữ liệu có version, `parent_version`, khôi phục được; không xoá — đánh dấu `stale`.
* Nội dung AI gắn nguồn + kết quả Fact Check theo từng claim.
* **Adapter + env cho mọi capability bên ngoài**: local-first, kích hoạt provider bằng API key, failover theo chain, `ALLOW_PAID` chặn chi phí ngoài ý muốn.
* Tách service theo đo đạc thực tế, nhưng contract (Pydantic/event schema) thiết kế để tách được từ ngày đầu.
* Ngôn ngữ nội dung mặc định: **tiếng Việt** (đa ngôn ngữ là thuộc tính cấp Project).

---

# 11. Lộ trình triển khai theo Phase

## Phase 1 — Nền tảng (tuần 1–6): Mode 2 chạy đầy đủ, 0 API key

* Tuần 1: Scene JSON Schema v1 (Pydantic+Zod) + 1 template Remotion + Remotion Player preview; edge-tts tiếng Việt + subtitle sync. **DoD:** video 30s 9:16 từ JSON viết tay, giọng Việt, subtitle khớp.
* Tuần 2–3: pipeline LangGraph 6 node (Research → FactCheck → Write → Storyboard → Produce → Render); LLM local + free tier; search SearXNG; asset Pexels. **DoD:** topic → MP4, mọi bước có màn hình review.
* Tuần 4: Fact Check PASS/WARN/FAIL, state machine, versioning, cost tracking + daily cap. **DoD:** pipeline dừng đúng gate; dashboard chi phí chạy.
* Tuần 5–6: Provider framework FR-21 hoàn chỉnh (chain, failover, health check, ma trận UI Admin), Prompt Management, auth + RBAC. **DoD:** thêm 1 API key qua UI → provider tự tham gia chain không restart.

## Phase 2 — Tự động hoá & Publish (tuần 7–12)

* Mode 1 scheduler (gate `off` → `pass_only` theo thống kê).
* YouTube upload + Analytics; publish scheduler; khai báo AI-content.
* Tách Render Worker + Voice Worker qua NATS JetStream; render song song nhiều project.
* Format 16:9; template thứ 2, 3; BGM library.
* Nộp đơn TikTok Content Posting API / Facebook (thời gian duyệt nằm ngoài kiểm soát — fallback Download).

## Phase 3 — Scale & hoàn thiện (tuần 13+)

* Scale ngang worker pool theo queue; cân nhắc Kubernetes theo tải thực tế.
* Tách agent nghẽn thành service riêng (theo đo đạc).
* TikTok/Facebook/LinkedIn publish khi được duyệt; analytics đa nền tảng.
* Visual diff version, A/B prompt, multi-workspace/RBAC mở rộng, đa ngôn ngữ.
* Kích hoạt provider trả phí có chọn lọc (FPT.AI TTS, model mạnh) theo số liệu chất lượng/chi phí.

---

# 12. Rủi ro & biện pháp

| Rủi ro | Biện pháp |
|---|---|
| edge-tts (service không chính thức) bị chặn | TTS chain failover sang viXTTS/F5-TTS local — không gián đoạn |
| Free tier LLM đổi quota/chính sách | Chain đa provider + xoay key (FR-15); local luôn là fallback cuối |
| TikTok/Facebook từ chối duyệt API | Fallback Download vĩnh viễn; YouTube là kênh auto chính |
| Video AI bị giảm reach ("mass-produced content") | Gate human review, khai báo AI-generated, **đa dạng bố cục thực thi bằng engine** (không phải template tĩnh) — Layout Classifier post-pass chống lặp ≥4 layout class/video, theme dial khác biệt (specs/layout-engine.md §5.1, specs/video-taste.md) |
| GPU local không đủ (Qwen 32B / SDXL) | Hạ model size qua env; ảnh dùng stock trước |
| Remotion company license khi thương mại hoá | Review điều khoản trước khi thu tiền |
| Chi phí cloud tăng khi scale | `ALLOW_PAID` + daily cap + cost dashboard; quyết định paid dựa trên số liệu |
| Tách service quá sớm gây phức tạp | Nguyên tắc "tách theo đo đạc"; contract chuẩn bị sẵn từ Phase 1 |
