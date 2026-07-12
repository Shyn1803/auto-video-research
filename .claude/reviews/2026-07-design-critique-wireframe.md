# Review: Design Critique — Wireframe v3

**Reviewers:** design-critique / design-system skills, PO feedback · **Scope:** `docs/design/wireframe.html`, `docs/design/ux-design.md`, `docs/design/design-system.md`

## Findings
1. **Analytics didn't show real analysis** — original design was a flat metrics dump, not actual insight. Fixed: 3-tab analytics structure with a new Story 8.7 (Analytics Insights) — sample-size gating, `topic_group` classification, apply-to-Mode-1 confirmation flow.
2. **Admin menu combined too much into one menu** — original design had a single catch-all admin screen. Fixed: split into 5 separate menu items (vận hành / tự động hoá / cấu hình AI / người dùng / hàng đợi), each mapped to its own story.
3. **Screens were too sparse (text+image only)** — didn't reflect Remotion's actual layout range. Fixed: 11-layout gallery (Hero, TextFocus, MediaFull, MediaText, Comparison, BigNumber, Chart, VersusTable, List, Quote, Code) exposed in the scene editor, backed by the full Layout Engine redesign.
4. **Dashboard/workspace/pipeline needed rethinking** — flat project list, unclear stepper. Fixed: lifecycle-grouped dashboard (Chờ duyệt / Đang chạy / Đang làm dở / Đã đăng), 5-station stepper (merged Nội dung station), `done-warning` state, ProjectDrawer for project meta.

## Outcome
All four findings resulted in concrete backlog changes (see epic-01, epic-05, epic-08 story updates) and design-system.md component additions (ProjectDrawer §3.7, updated PipelineStepper §3.2, Dashboard pattern §4.2). No open items remain from this review round.

## Follow-up Knowledge Captured
None promoted to a standalone pattern/anti-pattern — these were UI/IA decisions specific to this product, already fully captured in `docs/design/`.
