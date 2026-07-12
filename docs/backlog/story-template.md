# Story Template & Definition of Ready

**Version:** 1.0 · Chuẩn bắt buộc cho mọi story trước khi vào sprint. Story mẫu đạt chuẩn: [stories/story-5.6-research-review.md](stories/story-5.6-research-review.md)

## Vì sao cần template này (đánh giá backlog hiện tại)

Story trong epic-01…10 hiện dừng ở mức "AC happy-path + tasks" — đủ để dev bắt đầu nhưng thiếu 5 thứ khiến dev phải tự đoán (nguồn số 1 của bug và rework):

1. **Không có UI states** — mỗi màn có 5 trạng thái (default/loading/empty/error/disabled) nhưng AC chỉ tả default.
2. **Không có edge cases & business rules biên** — ví dụ: claim bị override rồi user restore research version cũ thì verdict tính lại thế nào?
3. **Không có scope Out** — dev không biết đâu là ranh giới dừng.
4. **Không có test scenario đầy đủ** (Gherkin chỉ 1-2 kịch bản) và **không có analytics/audit events**.
5. **Không có câu hỏi mở đã chốt** — quyết định PO đưa ra trong lúc thảo luận không được ghi lại.

## Definition of Ready (story chỉ được kéo vào sprint khi đủ)

- [ ] Đủ các mục template dưới; không còn `TBD` ở Business Rules và AC
- [ ] Design ref trỏ tới màn/component cụ thể (wireframe v2 + design-system)
- [ ] Dependency đã xong hoặc có kế hoạch mock
- [ ] Dev đã đọc và estimate lại (planning poker nhanh) — chênh >2× so với BA thì thảo luận lại scope
- [ ] Câu hỏi mở = 0 (hoặc ghi rõ quyết định tạm + người quyết)

---

## TEMPLATE

```markdown
# Story {epic}.{n} — {Tên} ({points}đ)

**User story:** As a {persona}, I want {capability}, so that {value}.
**Bối cảnh & giá trị:** {2-3 câu: vì sao story này tồn tại, nối với FR nào, điều gì xảy ra nếu không làm}

## Scope
**In:** {gạch đầu dòng — làm gì}
**Out:** {gạch đầu dòng — dễ tưởng nhầm là thuộc story này nhưng KHÔNG — trỏ story chứa nó}

## Business Rules
{Đánh số BR-1, BR-2… — mọi quy tắc quyết định hành vi, kể cả biên. Đây là phần quan trọng nhất.}

## UI/UX
- Màn/component: {link wireframe.html#màn + design-system §}
- 5 states: default / loading / empty / error / disabled — {mô tả từng state hoặc "theo pattern X design-system"}
- A11y đặc thù: {keyboard, aria, focus — ngoài chuẩn chung}

## Data & API
- Bảng/cột đụng tới: {link database-schema §}
- Endpoint: {link api-spec §} — thay đổi contract? {có/không → nếu có, cập nhật spec trong PR}
- Events phát ra: {domain events + audit log}

## Acceptance Criteria (Gherkin — phủ happy / biên / lỗi / phân quyền)
AC-1 (happy): Given… When… Then…
AC-2 (biên): …
AC-3 (lỗi): …
AC-4 (quyền): …
{tối thiểu 4, thường 5-8}

## Test Notes
{Fixture cần thêm, điểm cần test tay, case tự động hoá theo test-plan tầng nào}

## Quyết định đã chốt
{Câu hỏi đã hỏi PO + câu trả lời + ngày — để dev không hỏi lại}

**Depends:** {story ids} · **Design:** {refs} · **FR:** {refs}
```

## Quy trình nâng cấp backlog hiện tại (rolling — không dừng dev)

1. **Không viết lại 55 story một lượt.** Nâng chuẩn theo just-in-time: story của sprint N+1 phải đạt DoR trước khi sprint N kết thúc (refinement 1 buổi/tuần, BA chuẩn bị trước, dev + PO review 30–45 phút).
2. Thứ tự nâng cấp: story tuần 1–2 (1.1–1.4, 2.1–2.2) → nâng ngay tuần này; phần còn lại theo lịch plan.md.
3. Story file riêng đặt tại `backlog/stories/story-{id}-{slug}.md`; epic file giữ bảng tóm tắt + link.
4. Sau mỗi sprint: retro AC nào mơ hồ gây hỏi lại → cập nhật template.
```
