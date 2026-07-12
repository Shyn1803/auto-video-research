# Backlog Index — Epic Breakdown

**Version:** 3.1 · **Mọi story viết đầy đủ theo template** ([story-template.md](story-template.md)): User story + Bối cảnh & giá trị · Scope In/Out · Business Rules đánh số · UI/UX 5 states + a11y · Data & API (contract impact) · AC phủ happy/biên/lỗi/quyền · Test Notes · Quyết định đã chốt (⏳ = đề xuất BA chờ PO xác nhận tại refinement). Lịch tổng: [plan.md](../plan.md).
**v3.0:** +7 story từ gap analysis luồng wireframe v2 (1.7, 4.7, 5.8, 5.9, 6.5, 7.5; 5.6 nâng 5đ). **v3.1:** nâng toàn bộ story lên đầy đủ template. **v3.2 (PO duyệt 2026-07-11):** stepper gộp còn **5 trạm** (Nội dung = Dàn ý + Kịch bản); dashboard nhóm vòng đời + thumbnail; +3 story mới: 🆕 **2.6 Bộ layout mở rộng 11 bố cục** (5đ), 🆕 **4.8 Điểm vào từ kịch bản có sẵn** (3đ), 🆕 **5.10 ProjectDrawer** (2đ); 1.3 +1đ — tổng **229 points / ~18 tuần**.

| Epic | File | Points | Tuần | Story mới v3.x |
|---|---|---|---|---|
| 1. Nền tảng + người dùng | [epic-01](epic-01-foundation.md) | 25 | 1–3 | 1.7 |
| 2. Scene JSON + Remotion + TTS + 11 layout | [epic-02](epic-02-scene-remotion.md) | 26 | 1–3 (2.6: 4–6) | 🆕 2.6 |
| 3. Provider framework | [epic-03](epic-03-provider-framework.md) | 18 | 3–5 | |
| 4. Pipeline AI + Layout Engine core + entry script | [epic-04](epic-04-ai-pipeline.md) | 33 | 5–8 | 4.7, 4.8; 4.6 nâng cấp engine |
| 5. Workspace UI (editor/review/running/version/drawer) | [epic-05](epic-05-editor-ui.md) | 28 | 4–8 | 5.8, 5.9, 🆕 5.10 |
| 6. Produce, Render & Download | [epic-06](epic-06-render.md) | 18 | 9–10 | 6.5 |
| 7. Mode 1 + Scheduler + hàng đợi duyệt | [epic-07](epic-07-automation.md) | 19 | 11–13 | 7.5 |
| 8. Publish & Analytics + Insights | [epic-08](epic-08-publish-analytics.md) | 24 | 12–15 | 8.7 |
| 9. NATS, Workers & Observability | [epic-09](epic-09-infra-workers.md) | 21 | 14–16 | |
| 10. Multi-platform, Hardening & Release | [epic-10](epic-10-release.md) | 18 | 15–18 | |
| | **Tổng** | **230** | **18 tuần** | |

## FR Coverage Map

| FR | Story |
|---|---|
| FR-01 Project | 1.3, 7.5 |
| FR-02 Research | 4.3, 5.6 |
| FR-03 Ranking | 4.4 |
| FR-04 Fact Check | 4.4, 5.6 |
| FR-05/06 Outline/Script | 4.5, 5.7 (trạm Nội dung), 4.8 (entry script) |
| FR-07/08 Storyboard/Scene JSON | 4.6, 2.1, 2.6 (11 layout) |
| FR-01 sửa/cài đặt project | 5.10 (drawer) |
| FR-09 Preview+Edit | 2.3, 5.1–5.4 |
| FR-10 Timeline | 5.5, 6.5 |
| FR-11 Render | 6.1, 6.2, 10.1, 10.2 |
| FR-12 Publish | 6.3, 8.1–8.4, 10.3 |
| FR-13 Analytics | 8.5, 8.6, 8.7 |
| FR-14 Prompt | 4.2 |
| FR-15 Keys | 3.4, 8.2 |
| FR-16 Scheduler | 7.1, 8.4 |
| FR-17 State machine | 1.4 |
| FR-18 Routing+Cost | 3.2, 3.3, 3.5 |
| FR-19 TTS | 2.4, 2.5, 6.1 |
| FR-20 Asset | 5.3, 6.1, 6.5 |
| FR-21 Provider env | 3.1–3.5, nghiệm thu 10.5 |
| Điều khiển run / UX nền | 4.7, 5.8, 5.9, 1.6 |
| Personas Admin (user mgmt) | 1.7 |
| NFR | 6.4, 9.1–9.6, 10.4, 10.5 |

## Chuẩn story & Definition of Ready

Mọi story theo [story-template.md](story-template.md); bản chi tiết đầy đủ nhất làm mẫu: [stories/story-5.6-research-review.md](stories/story-5.6-research-review.md). Story trong epic file là bản "template rút gọn" — đủ BR/AC để dev làm; nếu khi refinement thấy cần tách file chi tiết (nhiều quyết định PO), tạo file trong `stories/`.

## Định nghĩa Done chung

1. Code + test theo [test-plan.md](../test-plan.md); CI xanh.
2. AC verify được — cách verify ghi trong PR.
3. Đổi contract → cập nhật specs cùng PR ([dev-guide.md](../dev-guide.md) §5).
4. Story UI: khớp [wireframe.html](../design/wireframe.html) + đủ 5 states ([design-system.md](../design/design-system.md) §3).
