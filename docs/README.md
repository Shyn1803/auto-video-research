# Bộ tài liệu bàn giao — AI Content Research & Video Automation Platform

**Ngày bàn giao:** 2026-07-10 · **Trạng thái:** sẵn sàng cho DEV bắt đầu Phase 1

## Đọc theo thứ tự (dev mới vào)

1. [SRS.md](SRS.md) — Yêu cầu hệ thống v3.0: 21 FR, NFR, 2 mode. **Đọc trước tiên.**
2. [glossary.md](glossary.md) — Từ vựng thống nhất + 6 domain rules hay bị làm sai. **Đọc trước khi code.**
3. [plan.md](plan.md) — **Master plan 16 tuần liên tục đến Release v1.0**: lịch theo tuần cho 2 dev, critical path, 5 milestone, Release Checklist.
4. [ARCHITECTURE.md](ARCHITECTURE.md) — Kiến trúc, data model, event bus, deployment, 7 ADR.
5. [dev-guide.md](dev-guide.md) — Cấu trúc monorepo, chạy dev, pattern adapter, conventions, định nghĩa "đổi contract".
6. [backlog/epics.md](backlog/epics.md) — **Backlog index**: 10 epic tách file riêng ([epic-01](backlog/epic-01-foundation.md) → [epic-10](backlog/epic-10-release.md)), ~55 story chi tiết Tasks + AC + Depends + Design ref, phủ đến release.
7. [design/wireframe.html](design/wireframe.html) — **Wireframe tương tác 14 màn** (mở trong browser); mapping màn ↔ story tại [design/ux-design.md](design/ux-design.md) §8.

## Tài liệu tra cứu khi làm việc

| Tài liệu | Dùng khi |
|---|---|
| [specs/layout-engine.md](specs/layout-engine.md) | **Kiến trúc Layout Engine** (Gamma-style): AI chỉ sinh semantic — Classifier + Constraint preset quyết bố cục |
| [specs/video-taste.md](specs/video-taste.md) | Nguyên tắc "gu thẩm mỹ" cho motion/theme/chống lặp — chuyển thể từ taste-skill (web) sang video, có phần "không áp dụng" ghi rõ |
| [specs/remotion-integration.md](specs/remotion-integration.md) | API Remotion thật (Composition/Sequence/Player/renderMedia) neo vào Layout Engine + cách cài Remotion Agent Skills lúc code |
| [specs/scene-json-schema.md](specs/scene-json-schema.md) | Contract render (đầu ra resolved của Layout Engine) |
| [specs/database-schema.md](specs/database-schema.md) | Viết model/migration — DDL đầy đủ + ERD |
| [specs/api-spec.md](specs/api-spec.md) | FE/BE làm song song — endpoint, error format, SSE, flow chuẩn |
| [specs/event-catalog.md](specs/event-catalog.md) | Phase 2+ — NATS subjects + payload |
| [specs/prompts.md](specs/prompts.md) | Seed prompt tiếng Việt cho 8 task LLM + quy trình eval |
| [CONFIGURATION.md](CONFIGURATION.md) | Mọi biến env, ma trận provider, 3 file .env mẫu (0đ → free-tier → paid) |
| [design/ux-design.md](design/ux-design.md) | Làm UI — IA, tokens, component list, UX patterns, **mapping design ↔ story (§8)** |
| [design/wireframe.html](design/wireframe.html) | Hợp đồng bố cục — so màn thật với wireframe khi nghiệm thu story UI |
| [test-plan.md](test-plan.md) | Viết test — tầng test, case bắt buộc, CI gate, DoD test |
| [runbook.md](runbook.md) | Vận hành — deploy, backup, sự cố thường gặp |

## Nguyên tắc không được vi phạm (tóm tắt)

1. **Local-first**: hệ thống chạy đầy đủ với 0 API key; provider trả phí chỉ hoạt động khi có key **và** `ALLOW_PAID=true`.
2. **Scene JSON là contract trung tâm** — một nguồn schema (Pydantic → JSON Schema → Zod), mọi thay đổi theo semver.
3. **Không ghi đè version** — mọi chỉnh sửa tạo version mới; restore đánh dấu stale, không xoá.
4. **Adapter cho mọi capability ngoài** — không gọi API provider trực tiếp từ business logic.
5. **Nội dung tiếng Việt, có nguồn, qua fact-check** — AI không tự bịa; render worker không fetch URL ngoài.

## Điểm bắt đầu

Story đầu tiên: **1.1 (repo scaffold)** và **2.1 (Scene JSON schema)** — chạy song song được bởi 2 dev. DoD tuần 1: video 30s 9:16 giọng Việt render từ Scene JSON viết tay.
