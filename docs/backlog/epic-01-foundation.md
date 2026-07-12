# Epic 1 — Nền tảng: repo, auth, project, state machine, versioning, người dùng

**Goal:** Dev thứ 2 clone repo `make up` chạy được; đăng nhập, tạo project, state machine + versioning hoạt động; admin quản lý được user.
**Points:** 25 · **Tuần:** 1–3 · Mọi story theo đủ mục [story-template.md](story-template.md). Ghi chú chung: "states: theo pattern chung" = default/loading/empty/error/disabled theo design-system §3; "Quyết định" đánh dấu ⏳ = đề xuất BA, PO xác nhận tại refinement.

---

# Story 1.1 — Khởi tạo monorepo & môi trường dev (3đ)

**User story:** As a developer, I want repo scaffold + docker-compose dev chạy bằng 1 lệnh, so that cả team bắt đầu trên cùng nền từ ngày 1.
**Bối cảnh & giá trị:** Mọi story khác build trên story này. Chuẩn hoá từ đầu (cấu trúc, lint, CI) rẻ hơn 10 lần so với retrofit; đây cũng là nơi "hợp đồng" dev-guide được hiện thực thành code.

## Scope
**In:** cấu trúc monorepo đúng dev-guide §1; compose base + dev (postgres16+pgvector, minio, searxng, ollama profile `gpu`); Makefile (`up/migrate/backend/frontend/test/gen-scene-schema/gen-api-client`); FastAPI skeleton (pydantic-settings, alembic init, `/health`); Next.js + Tailwind + shadcn init; **cài Remotion Agent Skills** (`npx skills add remotion-dev/skills` trong `packages/remotion-templates/` — [remotion-integration.md](../specs/remotion-integration.md) §1, dùng cho toàn bộ story chạm Remotion 2.x/6.2/9.2); CI (ruff/eslint/mypy + test + schema-gate stub); `.env.example` đầy đủ theo CONFIGURATION.md.
**Out:** compose prod + monitoring (9.5); seed nghiệp vụ (1.2 admin, 4.2 prompts); NATS (9.1).

## Business Rules
- **BR-1:** `make up` không yêu cầu GPU — profile gpu opt-in; máy không GPU stack vẫn lên đủ (trừ ollama).
- **BR-2:** chỉ api/frontend expose port; postgres/minio/searxng/ollama trong network nội bộ.
- **BR-3:** CI chạy được trên runner không GPU/không Docker-GPU.
- **BR-4:** `.env.example` là nguồn tham chiếu env duy nhất — thêm env mới ở code mà thiếu trong example → CI fail (script so khớp pydantic-settings ↔ example).

## UI/UX
Không có UI (trừ trang login placeholder từ Next scaffold). N/A 5 states.

## Data & API
- Bảng: chưa (alembic init rỗng). Endpoint: `GET /health` → `{status, version, db: ok}`.
- Contract change: khởi tạo — tạo file OpenAPI đầu tiên.

## Acceptance Criteria
1. **(happy)** Given máy mới có Docker+git, When clone → `cp .env.example .env` → `make up && make migrate`, Then services healthy, `/health` 200 kèm db ok, `next dev` hiện trang login.
2. **(biên/BR-1)** When chạy máy không GPU, Then stack lên đủ (ollama skip), README ghi hạn chế.
3. **(lỗi)** When port 5432 bận, Then lỗi in hướng dẫn đổi `POSTGRES_PORT` (không stack trace trần).
4. **(CI/BR-4)** PR đầu: lint+test pass; thêm 1 setting vào code thiếu example → CI fail đúng thông điệp.

## Test Notes
Smoke script `make verify-dev` (được CI gọi): up → health → down. Không cần fixture.

## Quyết định đã chốt
- ⏳ Python 3.12 + uv, Node 20 LTS — đề xuất BA theo dev-guide, PO xác nhận (ảnh hưởng image base).

**Depends:** — · **Design:** — · **FR:** AR-1, AR-8

---

# Story 1.2 — Auth JWT + RBAC (3đ)

**User story:** As a user, I want đăng nhập an toàn với vai trò admin/creator, so that dữ liệu và thao tác được bảo vệ đúng người.
**Bối cảnh & giá trị:** Nền của mọi kiểm soát quyền (🅐/🅞 trong api-spec). Làm sai ở đây thì audit, RBAC, publish đều mất giá trị; refresh-rotate chống chiếm phiên là yêu cầu NFR-4.

## Scope
**In:** bảng `users`, `refresh_tokens` (schema §2.1); argon2id; seed admin từ `ADMIN_EMAIL/PASSWORD`; endpoints `/auth/login|refresh|logout|me` (api-spec §1); refresh cookie httpOnly + rotate; dependency `require_role()`; rate limit login (slowapi); FE trang Login + AuthProvider + interceptor auto-refresh.
**Out:** CRUD user (1.7); quên mật khẩu qua email (v1.1 — ghi nhận); SSO (ngoài scope v1).

## Business Rules
- **BR-1:** access 15' / refresh 7d rotate; refresh token cũ bị dùng lại → revoke **cả chuỗi** (phát hiện token bị đánh cắp) + ghi audit.
- **BR-2:** 5 lần sai/15' theo cặp email+IP → 429 kèm `retry_after`.
- **BR-3:** user `is_active=false` → 401 ngay cả khi token còn hạn (check mỗi request qua cache 60s).
- **BR-4:** mật khẩu tối thiểu 10 ký tự; hash argon2id tham số chuẩn OWASP.

## UI/UX
- Màn: wireframe **Login**. States: default (form) · loading (nút spinner, form khoá) · error (message dưới form + `aria-live`, đếm ngược khi 429) · empty N/A · disabled N/A.
- A11y: submit bằng Enter; label gắn input; lỗi được screen reader đọc.

## Data & API
- Bảng: `users`, `refresh_tokens` (+ index theo schema §2.1). Endpoint: §1 api-spec đúng nguyên trạng.
- Events/audit: login fail vượt ngưỡng → log security; revoke chuỗi → audit record.
- Contract change: không (theo spec sẵn).

## Acceptance Criteria
1. **(happy)** Login đúng → access + cookie; `GET /auth/me` trả user; refresh rotate hoạt động.
2. **(biên/BR-1)** Dùng lại refresh đã rotate → 401 + cả chuỗi revoke; đăng nhập lại bình thường.
3. **(lỗi/BR-2)** Sai 5 lần → 429 + retry_after; UI hiện đếm ngược.
4. **(quyền)** Creator gọi route 🅐 → 403 error body chuẩn; admin 200.
5. **(biên/BR-3)** Khoá user đang có token sống → request kế ≤60s bị 401.

## Test Notes
Unit đủ nhánh token service (rotate/reuse/expire); integration login flow; fixture 2 user (admin/creator) dùng chung toàn test suite. Không gọi network ngoài.

## Quyết định đã chốt
- ⏳ Không "remember me" v1 (refresh 7d là đủ) — đề xuất BA.

**Depends:** 1.1 · **Design:** wireframe **Login** · **FR:** NFR-4

---

# Story 1.3 — Project CRUD + Dashboard nhóm vòng đời (5đ — +1đ thumbnail/nhóm, PO 2026-07-11)

**User story:** As a Content Creator, I want tạo/sửa/clone/lưu trữ dự án và thấy ngay việc cần làm tiếp trên mỗi dự án, so that quản lý nhiều video cùng lúc không sót việc.
**Bối cảnh & giá trị:** Dashboard là màn vào ra nhiều nhất mỗi ngày. "Hành động tiếp theo click được" (BR-3) là quyết định UX chủ chốt từ design-critique — biến dashboard từ danh sách thành hàng đợi việc.

## Scope
**In:** CRUD projects (api-spec §2) + ownership 🅞; modal Tạo dự án (topic bắt buộc; format mặc định 9:16, chọn thêm 16:9; giọng mặc định nữ + nghe thử); Dashboard khối "Dự án của tôi" (card: tên + StatusBadge + hành động tiếp theo), filter/paging/search; clone; archive/unarchive; empty state first-run.
**Out:** khối "Chờ duyệt hôm nay" (7.5); mini-stepper trên card (thêm 1 field sau 4.1); xoá vĩnh viễn dữ liệu (không có trong v1 — chỉ archive).

## Business Rules
- **BR-1:** DELETE chỉ khi DRAFT chưa có step_version; ngược lại 409 + UI gợi ý Lưu trữ.
- **BR-2:** clone copy version mới nhất mọi step + asset refs; không copy renders/publishes; tên mặc định "{tên} (bản sao)".
- **BR-3:** "hành động tiếp theo" suy từ status: NEED_REVIEW→"Mở duyệt ▸" (deep-link đúng tab), RUNNING→"● {bước} x%", READY→"Xem & đăng", FAILED→"Xem lỗi & chạy tiếp".
- **BR-4:** archive ẩn khỏi list mặc định; "Xem tất cả" gồm lưu trữ + khôi phục; project archive read-only.
- **BR-6 (mới, PO 2026-07-11):** dashboard nhóm theo vòng đời, thứ tự: Chờ duyệt (7.5) → Đang chạy → Đang làm dở → Đã đăng 7 ngày; nhóm rỗng ẩn; card có thumbnail (frame cảnh 1 — placeholder khi chưa có) + "bước x/5 · tên trạm", **không** mini-stepper.
- **BR-7 (mới):** filter chiều Mode (Tất cả / Của tôi / Tự động).
- **BR-5:** nghe thử giọng trong modal tạo gọi tts-preview với câu mẫu cố định (cache — không tốn).

## UI/UX
- Màn: wireframe **Dashboard** + **Tạo dự án** (modal). States: default · loading (skeleton 3 card) · empty (CTA "Tạo dự án đầu tiên" đúng wireframe) · error (banner + thử lại) · disabled N/A.
- A11y: card là link (Enter mở); modal focus-trap, ESC đóng; search có label.

## Data & API
- Bảng: `projects` (schema §2.2). Endpoints: §2 api-spec; thêm query `archived=true`.
- Contract change: **có** — thêm field `next_action {label, href}` vào response list (BR-3, server tính) → cập nhật api-spec §2 trong PR.

## Acceptance Criteria
1. **(happy)** Tạo topic "GPT-5.5" (9:16, giọng nữ) → card DRAFT; mở → workspace stepper chỉ Nghiên cứu mở.
2. **(biên/BR-2)** Clone project 8 cảnh → đủ version+scene, DRAFT, không renders; tên "(bản sao)".
3. **(lỗi/BR-1)** DELETE project có script → 409; toast gợi ý Lưu trữ hoạt động.
4. **(quyền)** Creator A không thấy project B ở list lẫn direct URL (403).
5. **(empty)** User mới → empty state đúng wireframe; tạo xong biến mất.
6. **(BR-3)** Seed 4 project 4 status → 4 nhãn hành động đúng, click đến đúng nơi.

## Test Notes
Integration CRUD + quyền (2 user fixture 1.2); Playwright: tạo → thấy card → mở. Fixture 4 status cho BR-3.

## Quyết định đã chốt
- Giọng đọc là thuộc tính project (không per-scene mặc định) — theo SRS FR-19; per-scene override vẫn có ở editor (PO ngầm duyệt qua wireframe).
- ⏳ Giới hạn 50 project active/user (chống rác) — đề xuất BA.

**Depends:** 1.2 · **Design:** wireframe **Dashboard**, **Tạo dự án** · **FR:** FR-01

---

# Story 1.4 — State machine + status_history (5đ)

**User story:** As a system, I want mọi chuyển trạng thái project đi qua một cổng duy nhất có kiểm tra và audit, so that pipeline resume chính xác sau lỗi và mọi thay đổi truy vết được.
**Bối cảnh & giá trị:** FR-17 là xương sống độ tin cậy: LangGraph resume (4.1), hàng đợi duyệt (7.5), gate Mode 1 (7.3) đều đọc status. Một chỗ ghi status "chui" là một bug resume tương lai.

## Scope
**In:** ma trận cạnh FR-17 dạng data (một nguồn cho code + test + docs); service `ProjectStateMachine.transition()` (validate cạnh, ghi history actor/reason, phát event `project.status`); `previous_status` cho FAILED/CANCELLED; API `GET status-history`.
**Out:** UI timeline lịch sử (5.9 History); cạnh CANCELLED chi tiết (4.7 bổ sung cạnh, dùng cùng service).

## Business Rules
- **BR-1:** mọi write `projects.status` ngoài service bị cấm — enforced bằng CI grep + code review.
- **BR-2:** actor bắt buộc: user uuid | `system` | tên node; reason bắt buộc với cạnh bất thường (→FAILED, override).
- **BR-3:** FAILED/CANCELLED giữ `previous_status`; resume chỉ về đúng trạng thái đó.
- **BR-4:** ARCHIVED đến từ trạng thái kết thúc (PUBLISHED/FAILED/DRAFT/READY); không từ trạng thái đang chạy.
- **BR-5:** transition idempotent-safe: chuyển tới trạng thái hiện tại → no-op trả 200 (chống double-click), trừ cạnh có side-effect.

## UI/UX
Không màn riêng — StatusBadge mọi nơi phản ánh status (map duy nhất design-system §3.1).

## Data & API
- Bảng: cột `status` + `status_history` (schema §2.2). Event: `project.status` (event-catalog).
- Contract change: không.

## Acceptance Criteria
1. **(happy)** APPROVED→PRODUCING: status đổi + history đủ actor/reason + event phát.
2. **(biên/BR-3)** FAILED từ RENDERING → resume → RENDERING, không về DRAFT.
3. **(lỗi)** PUBLISHED→RESEARCHING → 409 STATE_CONFLICT body chuẩn.
4. **(biên/BR-5)** Gọi 2 lần cùng transition → lần 2 no-op 200, history 1 dòng.
5. **(test)** Parametrize 100% cạnh hợp lệ + đại diện cạnh cấm; CI grep pass.

## Test Notes
Ma trận cạnh export ra bảng trong PR để PO/BA soát 1 lần. Property test: random walk chỉ đi cạnh hợp lệ không bao giờ raise.

## Quyết định đã chốt
- PUBLISHING tách khỏi READY (đã có trong FR-17 v3 SRS) — giữ.

**Depends:** 1.3 · **Design:** StatusBadge §3.1 · **FR:** FR-17

---

# Story 1.5 — Versioning engine (5đ)

**User story:** As a Content Creator, I want mọi bước có phiên bản với quan hệ nguồn gốc và khôi phục an toàn, so that tôi thử nghiệm nội dung thoải mái mà không sợ mất gì.
**Bối cảnh & giá trị:** "Mọi dữ liệu có version và khôi phục được" là nguyên tắc thiết kế số 4 của SRS. Quy tắc cascade-stale (không xoá, chỉ đánh dấu) là quyết định đã chốt từ v2.0 SRS — engine này hiện thực nó.

## Scope
**In:** bảng `step_versions`; service: create (auto-increment, parent_version), current (max không-stale), restore (cascade stale xuôi dòng theo thứ tự step), compare (text diff outline/script; scene-diff theo scene_id cho storyboard/scene_set); API §3 api-spec.
**Out:** UI VersionSwitcher/So sánh (5.9); visual diff preview (v1.1); nén/dọn version cũ (v1.1 — JSONB rẻ).

## Business Rules
- **BR-1:** không bao giờ UPDATE content — chỉ INSERT version mới.
- **BR-2:** restore tạo bản ghi hành động (actor) — không xoá, không sửa version nào.
- **BR-3:** stale chỉ đánh xuôi dòng (restore research không stale chính nó).
- **BR-4:** current = max(version) WHERE NOT stale; nếu tất cả stale → max(version) kèm cờ `all_stale` (UI cảnh báo).
- **BR-5:** regenerate khi user đã sửa tay → version mới `parent_version` = bản user-sửa (không mất công sửa).
- **BR-6:** compare chỉ trong cùng step; khác step → 400.

## UI/UX
Engine — UI ở 5.9. Response restore phải đủ dữ liệu cho UI: danh sách step bị stale.

## Data & API
- Bảng: `step_versions` (schema §2.3). Endpoints §3.
- Contract change: **có** — response restore thêm `staled_steps: []`; compare scene_set định dạng `{added[], removed[], changed[{scene_id, fields[]}]}` → cập nhật api-spec §3.

## Acceptance Criteria
1. **(happy)** research v1,v2 + script v1(parent rv2): restore rv1 → script stale; response `staled_steps=[script]`.
2. **(biên/BR-5)** User sửa script v2 → regenerate → v3 parent=v2; diff v2↔v3 đúng phần AI đổi.
3. **(biên/BR-4)** Mọi version script stale → current trả max + cờ all_stale.
4. **(biên)** Compare 2 scene_set khác số cảnh → added/removed/changed đúng theo scene_id, đổi thứ tự không tính là changed.
5. **(lỗi)** Restore version không tồn tại → 404; restore khi project RUNNING → 409.

## Test Notes
Property test cascade: chuỗi thao tác ngẫu nhiên (create/restore) → bất biến "current luôn xác định được", "không mất version nào". Fixture chuỗi 3 bước × 3 version.

## Quyết định đã chốt
- Giữ version vô hạn trong v1 (không auto-prune) — chi phí JSONB chấp nhận được (PO 2026-07-10, qua nguyên tắc "không xoá").

**Depends:** 1.4 · **Design:** — · **FR:** SRS §6

---

# Story 1.6 — Event bus nội bộ + SSE (2đ)

**User story:** As a frontend, I want nhận tiến độ pipeline realtime, so that user luôn thấy hệ thống đang sống và đang làm gì.
**Bối cảnh & giá trị:** RunningState (5.8) — pattern quan trọng nhất từ design-critique — sống bằng dữ liệu của story này. Interface bus phải giống NATS ngay từ đầu để 9.1 swap không đổi call-site (quyết định kiến trúc AR-5).

## Scope
**In:** in-process async bus (publish/subscribe, interface = NATS publisher tương lai); `GET /events/stream` SSE (auth one-time-token qua query); hook FE `useEventStream(projectId)` + reconnect; fallback polling `GET runs/{run_id}`.
**Out:** NATS thật (9.1); notification ngoài (7.4); event persistence (bus nội bộ là fire-and-forget — chấp nhận mất event khi restart, FE tự sync bằng polling).

## Business Rules
- **BR-1:** event format đúng api-spec §10 + envelope event-catalog từ ngày 1.
- **BR-2:** stream filter theo quyền — creator chỉ nhận event project mình; admin nhận tất.
- **BR-3:** one-time-token TTL 60s, dùng 1 lần (SSE không gửi được header Authorization).
- **BR-4:** FE reconnect → gọi polling 1 lần để sync trạng thái bị lỡ (bù fire-and-forget).

## UI/UX
Không màn riêng; tiêu thụ bởi RunningState/stepper/dashboard card.

## Data & API
- Endpoint mới: `POST /events/token` (lấy one-time token) + `GET /events/stream?token=` → **cập nhật api-spec §10** (bổ sung cơ chế token).
- Events: `project.status`, `step.progress` (đủ cho epic này; render/cost thêm dần).

## Acceptance Criteria
1. **(happy)** Run chạy → FE nhận step.progress ≤1s, đúng format.
2. **(biên/BR-4)** Ngắt mạng 10s giữa run → reconnect + sync → UI đúng trạng thái hiện tại.
3. **(quyền/BR-2)** 2 session creator khác nhau → không nhận chéo event (test tự động).
4. **(lỗi/BR-3)** Token quá 60s / dùng lần 2 → 401.

## Test Notes
Integration 2-client; contract test format event so với event-catalog schema.

## Quyết định đã chốt
- Fire-and-forget cho bus nội bộ chấp nhận được vì polling bù (⏳ xác nhận — ảnh hưởng UX mất mạng dài).

**Depends:** 1.4 · **Design:** RunningState §3.4 · **FR:** NFR-1, AR-5

---

# Story 1.7 — Quản lý người dùng (Admin) (2đ) 🆕

**User story:** As an Admin, I want tạo/khoá/đổi vai trò người dùng, so that kiểm soát được ai dùng hệ thống và với quyền gì.
**Bối cảnh & giá trị:** Persona Admin trong SRS §3 có quyền "Quản lý người dùng" nhưng backlog v2 bỏ sót hoàn toàn — gap phát hiện khi rà luồng. Không có story này thì thêm thành viên thứ 3 vào hệ thống phải sửa DB tay.

## Scope
**In:** CRUD users 🅐 (api-spec §1); tab Quản trị › Người dùng (list, tạo với mật khẩu tạm, đổi role, khoá/mở); audit thao tác; revoke phiên khi khoá (nối 1.2 BR-3).
**Out:** self-service đổi/quên mật khẩu (v1.1); mời qua email (v1.1 — v1 admin đưa mật khẩu tạm trực tiếp); nhóm/workspace (ngoài scope v1).

## Business Rules
- **BR-1:** không tự khoá/hạ quyền chính mình.
- **BR-2:** khoá user → mọi refresh token revoke ngay.
- **BR-3:** luôn còn ≥1 admin active — thao tác vi phạm → 409 kèm giải thích.
- **BR-4:** mật khẩu tạm buộc đổi ở lần đăng nhập đầu (cờ `must_change_password`).

## UI/UX
- Màn: wireframe **Quản trị › Người dùng**. States: default · loading skeleton bảng · empty (chỉ có mình → dòng hướng dẫn thêm) · error banner · disabled (nút thao tác trên chính mình disabled kèm tooltip BR-1).
- A11y: bảng có caption; select role có label; hành động khoá confirm dialog.

## Data & API
- Bảng: `users` (+cột `must_change_password`); audit vào bảng chung. Endpoints §1 🅐.
- Contract change: **có** — thêm `must_change_password` flow vào `/auth/login` response → cập nhật api-spec §1.

## Acceptance Criteria
1. **(happy)** Tạo creator + mật khẩu tạm → đăng nhập được → bị buộc đổi mật khẩu → vào bình thường.
2. **(biên/BR-2)** Khoá user đang đăng nhập → request kế ≤60s 401.
3. **(lỗi/BR-3)** Khoá admin cuối → 409 giải thích rõ.
4. **(quyền)** Creator không thấy tab; API → 403.
5. **(BR-1)** Nút khoá/đổi role trên dòng chính mình disabled + tooltip.

## Test Notes
Dùng fixture 2 user; thêm case 1 admin duy nhất. Playwright: khoá → session kia văng.

## Quyết định đã chốt
- ⏳ V1 không email mời — admin đưa mật khẩu tạm trực tiếp (đội nhỏ nội bộ).

**Depends:** 1.2 · **Design:** wireframe **Quản trị › Người dùng** · **FR:** Personas §3
