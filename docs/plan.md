# Master Plan — Từ khởi đầu đến Release v1.0

**Version:** 2.0 · Thay thế lộ trình "3 Phase" trong SRS §11 bằng **một kế hoạch liên tục 16 tuần** đi thẳng đến production release.
**Giả định nguồn lực:** 2 fullstack dev (DEV-A thiên backend/AI, DEV-B thiên frontend/Remotion) + 1 PO (duyệt nội dung, quyết định sản phẩm). Điều chỉnh tuyến tính nếu khác.

---

# 1. Phạm vi Release v1.0 (Definition of Release)

Hệ thống được coi là **release** khi tất cả điều sau đúng trên môi trường production:

1. **Mode 2** hoàn chỉnh: topic → video MP4 (9:16 và 16:9) với review/sửa/version ở mọi bước.
2. **Mode 1** chạy scheduler hàng ngày, gate `pass_only`, dừng ở READY chờ duyệt 1 click.
3. **Publish**: Download + YouTube auto-upload (kèm AI disclosure); TikTok/Facebook/LinkedIn adapter hoàn thiện ở mức code, kích hoạt bằng key khi app được duyệt (việc duyệt nằm ngoài kiểm soát — **không chặn release**).
4. **Analytics**: YouTube API + nhập tay các nền tảng khác, dashboard hoạt động.
5. **Hạ tầng**: NATS + render/voice worker tách, scale bằng replicas; monitoring (Prometheus/Grafana/Langfuse/Sentry) + alert; backup tự động + đã test restore.
6. **Local-first đạt chuẩn FR-21**: chạy đủ pipeline với 0 API key; ma trận provider trong Admin.
7. Vượt **Release Checklist** (§6).

Ngoài phạm vi v1.0 (ghi nhận cho v1.1+): visual diff version, A/B prompt, multi-workspace, đa ngôn ngữ ngoài tiếng Việt, Kubernetes.

---

# 2. Cấu trúc backlog

Backlog chia 10 epic, chi tiết từng story tại [backlog/](backlog/epics.md):

| Epic | Tên | Points | File |
|---|---|---|---|
| 1 | Nền tảng + người dùng | 24 | [epic-01](backlog/epic-01-foundation.md) |
| 2 | Scene JSON + Remotion + TTS tiếng Việt | 21 | [epic-02](backlog/epic-02-scene-remotion.md) |
| 3 | Provider framework | 18 | [epic-03](backlog/epic-03-provider-framework.md) |
| 4 | Pipeline AI + Layout Engine core + entry script | 33 | [epic-04](backlog/epic-04-ai-pipeline.md) |
| 5 | Workspace UI (editor/review/running/version) | 26 | [epic-05](backlog/epic-05-editor-ui.md) |
| 6 | Produce, Render & Download | 18 | [epic-06](backlog/epic-06-render.md) |
| 7 | Mode 1 + Scheduler + hàng đợi duyệt | 19 | [epic-07](backlog/epic-07-automation.md) |
| 8 | Publish & Analytics + Insights | 24 | [epic-08](backlog/epic-08-publish-analytics.md) |
| 9 | NATS, Workers & Observability | 21 | [epic-09](backlog/epic-09-infra-workers.md) |
| 10 | Multi-platform, Hardening & Release | 18 | [epic-10](backlog/epic-10-release.md) |
| | **Tổng** | **230** | ≈ **18 tuần** × 2 dev. v3.0: +7 story gap analysis. v3.2 (PO 2026-07-11): +2.6, +4.8, +5.10, 1.3 +1đ. v3.3 (PO 2026-07-11): kiến trúc **Layout Engine** (specs/layout-engine.md) — 4.6 nâng 5→6đ thành engine core; AI không chọn layout; solver tổng quát → v1.1 (§7). Đuôi lịch 17→18 tuần, M1–M5 giữ nguyên |

---

# 3. Lịch 16 tuần (critical path in đậm)

| Tuần | DEV-A (backend/AI) | DEV-B (frontend/Remotion) | Milestone |
|---|---|---|---|
| 1 | **1.1 scaffold**, 1.2 auth | **2.1 Scene schema**, 2.2 templates (bắt đầu) | |
| 2 | 1.3 project, **1.4 state machine** | 2.2 templates, **2.3 Player preview** | **M1: video 30s giọng Việt từ JSON tay** (2.4, 2.5 chung) |
| 3 | 1.5 versioning, 3.1 adapter base | 2.4 TTS + 2.5 subtitle (phối hợp A), 1.6 SSE | |
| 4 | **3.2 chain router**, 3.3 LLM adapters | 5.1 scene list + editor khung | |
| 5 | 3.4 keys, 3.5 cost, **4.1 LangGraph skeleton** | 5.2 edit controls, UI login/dashboard | **M2: provider framework xong — thêm key không restart** |
| 6 | 4.2 prompts, **4.3 research node** | 5.3 asset picker, 5.4 scene ops | |
| 7 | **4.4 ranking+factcheck** | 5.5 timeline UI | |
| 8 | 4.5 write node, **4.6 storyboard node** | UI research/factcheck/outline/script (màn 4.4–4.5 UX) | **M3: topic → scene_set full pipeline (MockLLM CI xanh)** |
| 9 | **6.1 produce node** | 6.3 màn render/download, polish editor | |
| 10 | **6.2 render orchestrator + cache** | 6.2 (phần worker Remotion), 6.4 benchmark | **M4: topic → MP4 download — dùng nội bộ hàng ngày từ đây (dogfooding)** |
| 11 | 7.1 scheduler, 7.2 Mode 1 pipeline | 8.1 publish adapter + UI publish | |
| 12 | 7.3 gate+stats, 7.4 notification | **8.2 YouTube OAuth**, 8.3 upload | |
| 13 | **9.1 NATS + 9.2 tách render worker** | 8.4 publish scheduler UI, 8.5 analytics collector | **M5: Mode 1 chạy sáng đầu tiên end-to-end** |
| 14 | 9.3 voice/asset worker, 9.4 DLQ | 8.6 analytics dashboard, 10.1 format 16:9 | |
| 15 | 9.5 Prometheus/Grafana, 9.6 Langfuse/Sentry | 10.2 template 2–3, 10.3 TikTok/FB/LinkedIn adapters | |
| 16 | **10.4 hardening**, 10.5 load test + backup drill | 10.6 release checklist + docs + go-live | **🚀 RELEASE v1.0** |

**Critical path:** 1.1 → 1.4 → 3.2 → 4.1 → 4.6 → 6.1 → 6.2 → 9.2 → 10.5 → release. Trễ ở đây = trễ release; các story UI có thể nở/co quanh nó.

**Quy tắc dogfooding:** từ M4 (tuần 10), PO dùng hệ thống tạo video thật mỗi ngày — bug thực tế được ưu tiên hơn story mới trong 20% capacity dự phòng.

---

# 4. Dependencies giữa epic

```
Epic 1 ──┬─→ Epic 3 ──→ Epic 4 ──┬─→ Epic 6 ──→ Epic 7 ──→ (M5)
         │                        │      │
Epic 2 ──┴────────→ Epic 5 ──────┘      └─→ Epic 8 ─┐
                                                     ├─→ Epic 10 → Release
Epic 6 ─────────────────────────→ Epic 9 ───────────┘
```

* Epic 1 & 2 song song từ ngày 1 (2 dev).
* Epic 5 (editor) cần 2.1 + 2.3; không cần đợi pipeline AI — dùng fixture scene.
* Epic 9 (NATS) cố ý đặt **sau** M4: tách worker khi pipeline đã chạy đúng in-process, chuyển giao contract đã ổn định.
* TikTok/FB app review (10.3): **nộp đơn ngay tuần 11** khi có video demo từ M4 — thời gian duyệt chạy song song, không chặn.

---

# 5. Quản lý rủi ro lịch

| Rủi ro | Kích hoạt | Phản ứng đã định trước |
|---|---|---|
| Benchmark render (6.4) tệ > 2× mục tiêu | tuần 10 | Cắt 10.2 (template 2–3) lấy chỗ tối ưu; NFR đàm phán lại với PO |
| Chất lượng LLM local kém tiếng Việt | tuần 6–8 | Chuyển tier cheap sang Gemini free (đổi env, đã thiết kế sẵn); không đổi code |
| edge-tts bị chặn giữa dự án | bất kỳ | 2.4 đã có adapter interface — chèn story viXTTS (5đ) vào tuần kế, lùi story UI ít quan trọng |
| 1 dev nghỉ/quá tải | bất kỳ | Cắt theo thứ tự: 10.2 → 8.4 → 7.3-stats → 10.3 (adapter code sang v1.1) — **không cắt** hardening 10.4/10.5 |
| YouTube API quota/verify chậm | tuần 12 | Release với YouTube ở chế độ "unverified app" (giới hạn user) — đủ cho dùng nội bộ, verify song song |

Buffer: mỗi tuần chỉ plan ~12 pts/13 pts khả dụng; tuần 16 không nhận story mới ngoài release checklist.

---

# 6. Release Checklist (gate cuối — tuần 16)

**Chức năng**
- [ ] E2E Playwright full journey xanh 3 lần liên tiếp trên staging
- [ ] Mode 1 chạy 5 sáng liên tiếp không can thiệp, gate hoạt động đúng (ít nhất 1 lần WARN dừng đúng)
- [ ] 10 video thật đã sản xuất và PO chấp nhận chất lượng (giọng, subtitle sync, hình)
- [ ] Chạy sạch với `.env` 0 API key (nghiệm thu FR-21/NFR-6)

**Vận hành**
- [ ] Backup tự động chạy + **restore drill thành công** trên máy sạch
- [ ] Alert nổ đúng khi: giết worker, đổ FAIL pipeline, vượt cost cap (diễn tập cả 3)
- [ ] Load test: 5 project render đồng thời, 20 user UI — không lỗi, số liệu ghi vào ARCHITECTURE.md
- [ ] Runbook được người **không viết code** làm theo để deploy từ đầu thành công

**Bảo mật**
- [ ] Rate limit hoạt động; secret không xuất hiện trong log (grep kiểm chứng); RBAC test đủ 🅐/🅞
- [ ] Fernet key rotation script chạy được; refresh token revoke hoạt động
- [ ] Dependency scan (pip-audit, npm audit) không critical

**Tài liệu & pháp lý**
- [ ] Docs specs khớp code (CI schema-sync xanh); CONFIGURATION.md đủ mọi env thực tế
- [ ] Mọi asset trong video mẫu có license record; AI disclosure bật mặc định
- [ ] Remotion license đã xác nhận phù hợp mục đích sử dụng

**Go-live:** tag `v1.0.0`, deploy prod theo runbook §1, bật schedule Mode 1, theo dõi 48h với alert — sau đó tuyên bố release.

---

# 7. Sau release (định hướng v1.1 — không cam kết lịch)

Kích hoạt TikTok/FB khi app duyệt xong; visual diff version; A/B prompt; đánh giá nâng cấp trả phí (FPT.AI TTS, model mạnh) theo 30 ngày số liệu. **Layout Engine v2:** constraint solver tổng quát (component tự khai `constraints{}` — layout là kết quả giải ràng buộc thay vì preset; kích hoạt khi cần >~15 class hoặc variants) + class Gallery/Timeline/lower-third + chart line/pie (specs/layout-engine.md §6).
