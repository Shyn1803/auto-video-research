# Task 9-3: Voice + Asset worker

**Points:** 3đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 9-1 · **FR:** NFR-2

## User story
As an operator, I want produce (TTS/asset) chạy worker riêng, tách được sang máy GPU, so that AI local nặng không tranh tài nguyên với API và scale độc lập.

## Why
NFR-2 phần media. Điểm giá trị thật: local TTS/SD cần GPU — worker tách host được (BR-2) mở đường "1 máy GPU + n máy CPU" của ARCHITECTURE §10.

## Scope
**In:** tách produce (6-1) thành consumer tts/asset.request trong worker Python (chung image backend, entrypoint riêng); bounded concurrency theo engine; compose profile GPU riêng (local TTS/SD).
**Out:** BGE-M3 tách service (chỉ khi nghẽn); autoscale.

## Business Rules
1. Cache audio/asset hiệu lực nguyên vẹn qua worker (6-1 BR-1).
2. Worker chạy host khác chỉ cần NATS_URL + MinIO + DB env — không phụ thuộc localhost.
3. Job TTS engine local khi GPU bận → xếp hàng theo semaphore, không OOM.

## Acceptance Criteria
1. **(happy)** Produce 10 cảnh qua worker; kill giữa chừng → resume không trùng audio (cache đo).
2. **(biên/BR-2)** Worker trên container network khác (giả lập host 2) → hoạt động đủ.
3. **(BR-3)** 10 job local TTS đồng thời, semaphore 2 → không OOM, xếp hàng đúng.
4. **(scale)** voice-worker=2 phân phối job.

## Data & API
Payload tts/asset.request-done theo event-catalog. Contract change: không.

## Decisions already locked
- ⏳ Voice và Asset chung 1 worker process v1 (2 consumer) — tách nữa khi số liệu đòi.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + reuse test 6-1 chạy chế độ worker (matrix); semaphore test với mock engine chậm.
