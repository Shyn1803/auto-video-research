# Operations Runbook

**Version:** 1.0 · Đối tượng: người vận hành (Admin) · Đi kèm [CONFIGURATION.md](CONFIGURATION.md), [ARCHITECTURE.md](ARCHITECTURE.md)

---

# 1. Deploy

## 1.1 Lần đầu

```bash
git clone <repo> && cd auto-video-research
cp .env.example .env             # điền JWT_SECRET, FERNET_MASTER_KEY (openssl rand -base64 32), ADMIN_EMAIL/PASSWORD
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
docker compose exec api alembic upgrade head   # + seed tự chạy
docker compose exec ollama ollama pull qwen2.5:14b-instruct
```

Kiểm tra sau deploy: `GET /health` (api), `GET /admin/providers` (ma trận provider đúng kỳ vọng), tạo 1 project test chạy hết pipeline.

## 1.2 Cập nhật phiên bản

```bash
git pull && docker compose build
docker compose exec api alembic upgrade head   # migration TRƯỚC khi swap container
docker compose up -d                            # rolling: api trước, worker sau
```

Rollback: `git checkout <tag cũ>` + `alembic downgrade <rev>` (mọi migration có downgrade thật — xem dev-guide) + `docker compose up -d`.

# 2. Backup / Restore

| Thành phần | Cách | Lịch |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` → MinIO bucket `backups/` + WAL archiving | daily (schedule `cleanup` kiêm) |
| MinIO | bucket versioning bật cho `videos/`; replicate sang host 2 (Phase 3) | liên tục |
| `.env` / secrets | bản mã hoá ngoài server (password manager) | mỗi lần đổi |

**Restore DB:** `pg_restore -c -d app backup.dump` → chạy `alembic current` xác nhận version → restart api/workers.
**Test restore mỗi quý** — backup chưa restore thử là chưa có backup.

# 3. Sự cố thường gặp

## 3.1 Pipeline FAILED

1. GET `/projects/{id}/runs/{run_id}` hoặc `status_history.reason` → node lỗi.
2. Lỗi `AllProvidersFailed` → xem §3.2. Lỗi validate scene → xem chi tiết 422 trong log, thường do prompt storyboard — thử regenerate.
3. Resume: POST `/projects/{id}/steps/{step}/run` — LangGraph checkpoint chạy tiếp từ node fail, không làm lại từ đầu.

## 3.2 Provider failover / hết quota

* Event `provider.exhausted` (Telegram) → key tự re-activate sau `exhausted_until`.
* Cần gấp: thêm key mới qua `/admin/api-keys` (áp dụng ngay, không restart) hoặc sửa `*_CHAIN` trong `.env` + `docker compose up -d api`.
* edge-tts bị chặn (lỗi 403 hàng loạt ở Voice Worker): đổi `TTS_CHAIN=local_tts,edge_tts` — cần GPU đã cài `TTS_LOCAL_MODEL`.

## 3.3 Cost cap

Event `cost.cap_reached` → pipeline pause toàn hệ thống. Xử lý: xem `/admin/costs` xác định task ngốn → hoặc nâng `DAILY_COST_CAP` (env, restart api) hoặc đợi 00:00 UTC tự reset. Project đang chạy resume bằng §3.1.3.

## 3.4 Render lỗi / chậm

* Job failed → `renders.error`. Lỗi thiếu asset: chạy lại produce. Lỗi Remotion (stack trace JS): thường do scene JSON ngoài `supportedSchemaRange` — kiểm tra version template worker (`docker compose images render-worker`).
* Queue dồn (GET `/admin/queue` pending cao): scale `docker compose up -d --scale render-worker=4`.
* Worker treo: JetStream tự redeliver sang worker khác sau ack_wait; kill container treo là an toàn (idempotent).

## 3.5 DLQ có message

GET `/admin/queue` → xem payload DLQ → sửa nguyên nhân gốc (thường: asset thiếu, schema lệch) → POST `/admin/queue/dlq/{stream}/replay`. Không replay khi chưa hiểu nguyên nhân — sẽ quay lại DLQ.

## 3.6 Ollama OOM / chậm

* OOM: hạ `OLLAMA_MODEL_*` xuống 7b, hoặc `num_ctx` thấp hơn (env `OLLAMA_NUM_CTX`).
* Chậm kéo dài: kiểm tra GPU util (`nvidia-smi`); nhiều request song song → tăng `OLLAMA_NUM_PARALLEL` hoặc chuyển tier cheap sang Gemini free.

## 3.7 Disk đầy (MinIO)

Alert ở 80%. Dọn: schedule `cleanup` xoá `renders/` cache > `RENDER_CACHE_TTL_DAYS` — chạy tay: POST `/admin/schedules/{cleanup}/run-now`. `videos/` không tự xoá — archive project cũ trước.

# 4. Bảo trì định kỳ

| Việc | Tần suất |
|---|---|
| Xem cost dashboard + tỉ lệ fact-check PASS đúng (quyết định MODE1_AUTOPUBLISH) | tuần |
| Test restore backup | quý |
| Update image (security patch), `docker compose pull` | tháng |
| Xoay `JWT_SECRET`? Không — xoay refresh bằng revoke; xoay `FERNET_MASTER_KEY` cần re-encrypt api_keys (script `make rotate-fernet`) | khi nghi lộ |
| Review DLQ + partition mới (tự động, xác nhận có chạy) | tháng |

# 5. Liên hệ & escalation

Điền khi có team: ai giữ server, ai giữ key provider, kênh alert (Telegram group), SLA nội bộ.
