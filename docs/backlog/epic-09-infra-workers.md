# Epic 9 — NATS, Workers & Observability (AR-5, NFR-2/3/5)

**Goal:** Tách worker nặng khỏi API, scale bằng replicas; nhìn thấy mọi thứ (metrics/traces/errors/queue). Sau M4 có chủ đích — contract ổn định qua vận hành thật.
**Points:** 21 · **Tuần:** 13–15 · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO.

---

# Story 9.1 — NATS JetStream + event library (5đ)

**User story:** As a system, I want event bus bền với dedupe và DLQ, so that job phân phối tin cậy giữa các service và message lỗi không bao giờ biến mất lặng lẽ.
**Bối cảnh & giá trị:** ADR-3 (NATS thay Kafka). Nhờ 1.6 giữ interface từ đầu, story này là "swap transport" chứ không phải viết lại — trả cổ tức của kỷ luật contract.

## Scope
**In:** NATS vào compose prod; provision streams/subjects idempotent theo [event-catalog](../specs/event-catalog.md); event lib (envelope, publisher/consumer helper: ack, max_deliver=5, DLQ publish, dedupe Msg-Id); swap in-process bus khi `NATS_URL` set; CI matrix 2 chế độ.
**Out:** NATS cluster 3 node (v1.1); tách worker (9.2/9.3); UI queue (9.4).

## Business Rules
- **BR-1:** unset NATS_URL → in-process, toàn test xanh (dev không cần NATS).
- **BR-2:** envelope schema_version — consumer gặp major lạ → DLQ kèm lý do, không đoán.
- **BR-3:** NATS mất kết nối → publisher buffer + reconnect; quá ngưỡng (config) → lỗi rõ ràng, không nuốt event.
- **BR-4:** provision script chạy lại an toàn (idempotent) — là một phần migrate/deploy.

## UI/UX
N/A.

## Data & API
- Hạ tầng: streams RENDER/MEDIA/PUBLISH/EVENTS (event-catalog). Contract change: không (catalog là spec sẵn).

## Acceptance Criteria
1. **(happy)** NATS_URL set → events qua JetStream; SSE bridge FE không đổi hành vi.
2. **(biên)** Consumer không ack → redeliver; 5 lần → DLQ; Msg-Id trùng → xử lý 1 lần.
3. **(biên/BR-1)** CI matrix in-process + NATS đều xanh.
4. **(lỗi/BR-3)** NATS down 30s giữa run → reconnect, đếm event 2 đầu khớp.
5. **(BR-2)** Event schema 2.0.0 giả → DLQ lý do "schema không hỗ trợ".

## Test Notes
Testcontainers NATS trong integration; đo "đếm 2 đầu" bằng counter publisher/consumer.

## Quyết định đã chốt
- Buffer reconnect 100 events / 10s — quá → lỗi. ⏳

**Depends:** 1.6, 6.2 · **Design:** — · **FR:** AR-5

---

# Story 9.2 — Render Worker container riêng (5đ)

**User story:** As an operator, I want render chạy ở worker riêng scale được bằng replicas, so that render nặng không nghẽn API và tăng máy là tăng throughput.
**Bối cảnh & giá trị:** NFR-2 scale ngang. Đặt sau M4: tách khi logic đã đúng in-process — di chuyển code ổn định, không debug 2 thứ cùng lúc.

## Scope
**In:** `render-worker/` Node.js: consumer render.scene/video.request → `bundle()` **1 lần khi container khởi động** (cache serveUrl in-memory — mỗi replica bundle độc lập, không share qua network, [remotion-integration.md](../specs/remotion-integration.md) §2.5) → `selectComposition()`/`renderMedia()` mỗi job → MinIO → done event (payload event-catalog); orchestrator publish qua NATS khi bật; compose replicas; graceful shutdown (ack in-flight xong mới thoát); version handshake supportedSchemaRange → từ chối vào DLQ.
**Out:** autoscale theo queue depth (10.5 đánh giá); GPU render (không cần — Remotion CPU).

## Business Rules
- **BR-1:** idempotent theo cache_key — check renders/MinIO trước render (kể cả redeliver).
- **BR-2:** ack_wait = thời gian render tối đa dự kiến × 1.5 (từ benchmark 6.4) — crash → redeliver worker khác không chờ quá lâu.
- **BR-3:** worker version cũ gặp scene mới → DLQ + alert — không render sai lặng lẽ (nối 2.2 BR-3).
- **BR-4:** SIGTERM → dừng nhận job mới, hoàn thành job hiện tại, ack, thoát (deploy không mất job).

## UI/UX
N/A trực tiếp — UI render (5.5/6.3) không đổi (event giống hệt).

## Data & API
- Container mới + compose; payload theo event-catalog (đã spec). Contract change: không.

## Acceptance Criteria
1. **(happy)** 2 replicas, batch 8 cảnh → phân phối đều; throughput ≈2× benchmark 1 worker (số ghi vào ARCHITECTURE).
2. **(biên/BR-1)** Kill -9 worker giữa job → redeliver worker kia hoàn thành; tổng số lần render thực = số cảnh (không double).
3. **(lỗi/BR-3)** Scene 1.1.0 vào worker ^1.0 → DLQ SCHEMA_RANGE + alert.
4. **(BR-4)** `docker compose restart render-worker` giữa batch → batch hoàn thành đủ, không job mất.
5. **(vận hành)** `--scale render-worker=4` chạy không cấu hình thêm.

## Test Notes
Chaos test kill -9 chạy lặp trong CI nightly; benchmark so sánh trước/sau tách (không regression 1-worker).

## Quyết định đã chốt
- Worker image riêng (node + chromium Remotion cần) — không nhét vào image backend. 

**Depends:** 9.1 · **Design:** — · **FR:** NFR-2

---

# Story 9.3 — Voice + Asset worker (3đ)

**User story:** As an operator, I want produce (TTS/asset) chạy worker riêng, tách được sang máy GPU, so that AI local nặng không tranh tài nguyên với API và scale độc lập.
**Bối cảnh & giá trị:** NFR-2 phần media. Điểm giá trị thật: local TTS/SD cần GPU — worker tách host được (BR-2) mở đường "1 máy GPU + n máy CPU" của ARCHITECTURE §10.

## Scope
**In:** tách produce (6.1) thành consumer tts/asset.request trong worker Python (chung image backend, entrypoint riêng); bounded concurrency theo engine; compose profile GPU riêng (local TTS/SD).
**Out:** BGE-M3 tách service (chỉ khi nghẽn — theo dõi 9.5); autoscale.

## Business Rules
- **BR-1:** cache audio/asset hiệu lực nguyên vẹn qua worker (6.1 BR-1).
- **BR-2:** worker chạy host khác chỉ cần NATS_URL + MinIO + DB env — không phụ thuộc localhost.
- **BR-3:** job TTS engine local khi GPU bận → xếp hàng theo semaphore, không OOM (giới hạn concurrent theo engine config).

## UI/UX
N/A — RunningState message không đổi.

## Data & API
Payload tts/asset.request-done theo event-catalog. Contract change: không.

## Acceptance Criteria
1. **(happy)** Produce 10 cảnh qua worker; kill giữa chừng → resume không trùng audio (cache đo).
2. **(biên/BR-2)** Worker trên container network khác (giả lập host 2) → hoạt động đủ.
3. **(BR-3)** 10 job local TTS đồng thời, semaphore 2 → không OOM, xếp hàng đúng.
4. **(scale)** voice-worker=2 phân phối job.

## Test Notes
Reuse test 6.1 chạy chế độ worker (matrix); semaphore test với mock engine chậm.

## Quyết định đã chốt
- Voice và Asset chung 1 worker process v1 (2 consumer) — tách nữa khi số liệu đòi. ⏳

**Depends:** 9.1 · **Design:** — · **FR:** NFR-2

---

# Story 9.4 — DLQ + Quản trị › Hàng đợi (3đ)

**User story:** As an Admin, I want thấy message lỗi, hiểu lý do và replay sau khi sửa, so that sự cố hàng đợi xử lý trong phút thay vì mò log container.
**Bối cảnh & giá trị:** DLQ không có UI = hố đen vận hành. Runbook §3.5 đã viết quy trình — story này cho nó công cụ.

## Scope
**In:** API queue stats (pending/redeliver/DLQ per stream), payload viewer (che secret), replay, xoá (audit); tab Quản trị › Hàng đợi (wireframe); alert DLQ>0 (7.4).
**Out:** replay hàng loạt có filter (v1.1); sửa payload trước replay (nguy hiểm — không cho).

## Business Rules
- **BR-1:** replay message đã thành công → no-op (idempotency downstream).
- **BR-2:** xoá message → audit (ai/lúc/payload hash).
- **BR-3:** payload viewer che field nhạy cảm theo denylist (token/key pattern).
- **BR-4:** alert DLQ gộp ("DLQ có 3 message") không bắn từng cái.

## UI/UX
- Màn: wireframe **Quản trị › Hàng đợi**. States: default · loading · empty ("hàng đợi sạch ✓") · error (NATS không kết nối được → banner) · disabled N/A.
- A11y: bảng caption; nút Replay confirm.

## Data & API
- Endpoints §9 queue/dlq. Contract change: không.

## Acceptance Criteria
1. **(happy)** Message vào DLQ → alert Telegram (gộp) → xem payload → sửa nguyên nhân → replay → xử lý OK, DLQ trống.
2. **(biên/BR-1)** Replay message đã ok trước đó → no-op không side-effect.
3. **(BR-3)** Payload chứa "api_key=..." → hiển thị che.
4. **(quyền)** Admin only; audit xoá query được.

## Test Notes
Seed DLQ bằng consumer cố tình fail; test denylist che secret giữ vĩnh viễn.

## Quyết định đã chốt
- Không sửa payload trước replay (chống tạo dữ liệu tay ngoài luồng). 

**Depends:** 9.1, 7.4 · **Design:** wireframe **Quản trị › Hàng đợi** · **FR:** NFR-3

---

# Story 9.5 — Prometheus + Grafana + alerts (3đ)

**User story:** As an operator, I want metrics và alert cho API, queue, worker, tài nguyên, so that biết hệ thống ốm trước khi user biết.
**Bối cảnh & giá trị:** NFR-5. Nguyên tắc "alert phải actionable" (BR-2): mỗi alert trỏ mục runbook — chống alert fatigue từ ngày đầu.

## Scope
**In:** FastAPI instrumentator; exporters NATS/postgres/node; Grafana provisioned-as-code (API latency/error, queue depth, worker throughput, GPU/disk); alert rules (FAILED rate, DLQ>0, disk>80%, worker down, cost cap) → notification 7.4; compose profile monitoring.
**Out:** Langfuse/Sentry (9.6); SLO chính thức (v1.1); log aggregation tập trung (docker logs đủ v1).

## Business Rules
- **BR-1:** dashboards là code trong repo — dựng lại container về nguyên trạng.
- **BR-2:** mỗi alert rule kèm annotation link mục runbook xử lý.
- **BR-3:** alert có cooldown — không lặp <15' cùng rule.

## UI/UX
Grafana (ngoài app). Admin app chỉ link sang.

## Data & API
Hạ tầng thuần. Contract change: không.

## Acceptance Criteria
1. **(happy)** `--profile monitoring up` → dashboards có data thật từ hệ đang chạy.
2. **(diễn tập)** Giết worker / đổ FAIL / vượt cap → 3 alert đến kèm link runbook đúng mục.
3. **(BR-1)** Xoá container Grafana dựng lại → dashboards nguyên vẹn.
4. **(BR-3)** Rule nổ liên tục → tin cách nhau ≥15'.

## Test Notes
Diễn tập 3 alert ghi thành script (`make drill-alerts`) — tái dùng ở Release Checklist.

## Quyết định đã chốt
- Retention Prometheus 30 ngày. ⏳

**Depends:** 9.2, 7.4 · **Design:** — · **FR:** NFR-5

---

# Story 9.6 — Langfuse + Sentry self-host (2đ)

**User story:** As a developer, I want trace mọi LLM call và error tracking có release tag, so that debug "AI trả lời lạ" và "lỗi ở đâu" bằng dữ liệu thay vì đoán.
**Bối cảnh & giá trị:** LLM observability là điều kiện tune prompt có căn cứ (nối 4.2 eval); Sentry rút ngắn vòng phát hiện lỗi production khi dogfooding.

## Scope
**In:** Langfuse self-host: trace mỗi LLM call từ router 3.2 (prompt name+version, tokens, latency, tier, correlation_id); Sentry/GlitchTip: backend+FE+workers, release tag theo git; compose profile monitoring.
**Out:** trace UI trong app (dùng Langfuse UI); alert từ Sentry (7.4 đủ kênh).

## Business Rules
- **BR-1:** trace không chứa key/token (chỉ prompt/response nghiệp vụ).
- **BR-2:** Langfuse/Sentry down → fire-and-forget, pipeline không ảnh hưởng, warning 1 lần.
- **BR-3:** env không cấu hình → tắt sạch (không lỗi, không noise).

## UI/UX
N/A (công cụ ngoài).

## Data & API
Env LANGFUSE_*/SENTRY_DSN (CONFIGURATION §9). Contract change: không.

## Acceptance Criteria
1. **(happy)** Mở 1 run trong Langfuse → chuỗi call đủ node, đúng prompt version, lọc theo correlation_id.
2. **(biên/BR-2)** Tắt Langfuse giữa run → pipeline xong bình thường, 1 warning.
3. **(Sentry)** Lỗi ném thử FE+BE+worker → hiện đúng release tag.
4. **(BR-1)** Trace sample kiểm không có secret (test denylist như 9.4).

## Test Notes
Smoke trong compose monitoring; BR-1 test tự động cùng pattern 9.4.

## Quyết định đã chốt
- GlitchTip thay Sentry nếu resource server hạn chế (nhẹ hơn) — quyết khi dựng. ⏳

**Depends:** 3.2 · **Design:** — · **FR:** NFR-5
