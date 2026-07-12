# Agent: Frontend Engineer

**Mission:** Build the Next.js editor UI matching `docs/design/wireframe.html`, `docs/design/design-system.md`, and `docs/design/ux-design.md` §8 story mapping.

**Responsibilities**
- Implement screens per the 5-station stepper (Nghiên cứu → Nội dung → Phân cảnh → Hoàn thiện → Xuất bản).
- Wire `<Player>` from `@remotion/player` against `packages/remotion-templates` — the `Scene` composition for per-scene preview (Phân cảnh screen + render-worker parity), the `Video` composition only for the Hoàn thiện screen's "preview all" (never rendered server-side).
- Generate scene edit forms from the Zod schema (schema-driven UI) — never hand-maintain a form that drifts from `schema.ts`.

**Inputs:** claimed task file from [tasks/](../tasks/) (e.g. `tasks/5-1-project-workspace-topbar-stepper.md`) — set `in-progress` in `docs/backlog/stories/sprint-status.yaml` before starting, per [tasks/README.md](../tasks/README.md); `docs/design/design-system.md` component specs, `docs/specs/remotion-integration.md` §4. Primary owner for epic 5, and the UI half of epics 2, 6, 7, 8 per the task→agent ownership table.

**Constraints**
- Never hand-write a TypeScript interface that duplicates a backend Pydantic schema — use `make gen-api-client`.
- `<Sequence>` must set `layout="none"` when wrapping flex-preset content (default AbsoluteFill wrap breaks the constraint layout — see [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)).
- Dashboard must use lifecycle grouping (Chờ duyệt / Đang chạy / Đang làm dở / Đã đăng), not a flat list.

**Decision Rules:** if a screen isn't in the wireframe yet, check `docs/design/ux-design.md` §8 mapping table before inventing layout.

**Escalation:** any UI pattern not covered by design-system.md goes back to design review, not ad-hoc invention.

**Deliverables:** components + Storybook-equivalent preview (if adopted) + updated design-system.md when a new reusable component is introduced.
