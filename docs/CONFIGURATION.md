# Configuration — Env & Provider Reference

**Version:** 1.0 · Đi kèm [SRS.md](SRS.md) v3.0 (FR-21) · [ARCHITECTURE.md](ARCHITECTURE.md)

Nguyên tắc: **hệ thống chạy đầy đủ với 0 API key** (local/self-host). Cung cấp key qua env hoặc UI Admin (FR-15) → provider tự tham gia chain. `ALLOW_PAID=false` mặc định chặn mọi provider tính phí kể cả khi có key.

---

# 1. Cơ chế chung

## 1.1 Chain & điều kiện kích hoạt

Mỗi capability có một biến `*_CHAIN` liệt kê provider theo thứ tự ưu tiên. Một provider **available** khi thoả cả 3:

1. Có mặt trong chain.
2. Điều kiện kích hoạt thoả: API key tồn tại (env hoặc DB) **hoặc** service local reachable (health check).
3. Nếu provider tính phí: `ALLOW_PAID=true`.

Runtime: provider lỗi (timeout / 5xx / hết quota) → chuyển provider kế tiếp + event `provider.failover`; hết chain → task fail, retry theo backoff.

## 1.2 Thứ tự ưu tiên nguồn cấu hình

`env` > `api_keys` trong DB (UI Admin) > default. Env dành cho deploy tự động; DB dành cho Admin thay đổi runtime không restart.

## 1.3 Startup validation

Khi khởi động, API log ma trận capability → provider active (và lý do provider bị loại: thiếu key, health fail, paid bị chặn). Ma trận này hiển thị ở UI Admin (FR-15).

---

# 2. Core

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `APP_ENV` | `development` | `development` / `production` |
| `ALLOW_PAID` | `false` | Chặn mọi provider có cost > 0 |
| `DAILY_COST_CAP` | `0` | USD/ngày; `0` = chỉ cho phép free (cùng hiệu lực ALLOW_PAID) |
| `DEFAULT_LANGUAGE` | `vi` | Ngôn ngữ nội dung mặc định |
| `MODE1_AUTOPUBLISH` | `off` | `off` / `pass_only` / `on` (xem SRS §2) |
| `JWT_SECRET` | — (bắt buộc) | |
| `FERNET_MASTER_KEY` | — (bắt buộc) | Mã hoá api_keys trong DB |
| `DATABASE_URL` | `postgresql://…@postgres:5432/app` | |
| `NATS_URL` | (rỗng = Phase 1, không dùng bus) | `nats://nats:4222` khi Phase 2+ |

---

# 3. LLM

## 3.1 Chain theo tier

| Biến | Mặc định |
|---|---|
| `LLM_CHAIN_CHEAP` | `ollama,gemini,openrouter_free` |
| `LLM_CHAIN_STRONG` | `gemini,groq,openrouter_free,openrouter_paid` |
| `EMBEDDING_CHAIN` | `bge_m3_local,gemini_embedding` |

## 3.2 Provider

| Provider | Kích hoạt bởi | Biến phụ | Phí |
|---|---|---|---|
| `ollama` | `OLLAMA_URL` reachable (mặc định `http://ollama:11434`) | `OLLAMA_MODEL_CHEAP=qwen2.5:14b-instruct`, `OLLAMA_MODEL_STRONG=qwen2.5:32b-instruct` | Free |
| `gemini` | `GEMINI_API_KEY` | `GEMINI_MODEL=gemini-flash-latest` | Free tier |
| `groq` | `GROQ_API_KEY` | `GROQ_MODEL` | Free tier |
| `openrouter_free` | `OPENROUTER_API_KEY` | tự lọc model tag `:free` | Free |
| `openrouter_paid` | `OPENROUTER_API_KEY` + `ALLOW_PAID=true` | `OPENROUTER_PAID_MODEL` | **Paid** |
| `mistral` | `MISTRAL_API_KEY` | | Free tier |
| `bge_m3_local` | model tồn tại local (tự tải lần đầu) | `EMBEDDING_DEVICE=cuda\|cpu` | Free |

Nhiều key cùng provider: `GEMINI_API_KEY_1..N` hoặc nhập qua UI — router xoay vòng khi hết quota.

---

# 4. TTS (giọng tiếng Việt)

| Biến | Mặc định |
|---|---|
| `TTS_CHAIN` | `edge_tts,local_tts,fpt` |
| `TTS_VOICE_FEMALE` | `vi-VN-HoaiMyNeural` |
| `TTS_VOICE_MALE` | `vi-VN-NamMinhNeural` |

| Provider | Kích hoạt bởi | Ghi chú | Phí |
|---|---|---|---|
| `edge_tts` | luôn có | word-timestamp cho subtitle | Free |
| `local_tts` | `TTS_LOCAL_MODEL=vixtts\|f5tts` + GPU | clone giọng (viXTTS) | Free |
| `fpt` | `FPT_API_KEY` + `ALLOW_PAID=true` | chất lượng cao nhất trong nhóm giọng Việt bản địa; có key → tự lên đầu chain nếu đặt trước trong `TTS_CHAIN` | **Paid** |
| `google_tts` | `GOOGLE_TTS_CREDENTIALS` + `ALLOW_PAID=true` | vi-VN Wavenet | **Paid** |
| `zalo` | `ZALO_API_KEY` + `ALLOW_PAID=true` | | **Paid** |
| `elevenlabs` | `ELEVENLABS_API_KEY` + `ALLOW_PAID=true` | giọng chất lượng cao nhất chain, đa ngôn ngữ; API call qua mạng ngoài — nếu chạy trong agent sandbox bị chặn mạng, xem [patterns/sandboxed-agent-network-fallback.md](../.claude/patterns/sandboxed-agent-network-fallback.md) để test/debug adapter cục bộ | **Paid** |

Subtitle align fallback: `SUBTITLE_ALIGNER=faster_whisper` (`WHISPER_MODEL=phowhisper-small`, local).

---

# 5. Search & Crawl

| Biến | Mặc định |
|---|---|
| `SEARCH_CHAIN` | `searxng,tavily,brave,serpapi` |

| Provider | Kích hoạt bởi | Quota free | Phí |
|---|---|---|---|
| `searxng` | `SEARXNG_URL` reachable (compose có sẵn) | không giới hạn | Free |
| `tavily` | `TAVILY_API_KEY` | 1.000 req/tháng | Free tier |
| `brave` | `BRAVE_API_KEY` | 2.000 req/tháng | Free tier |
| `serpapi` | `SERPAPI_KEY` + `ALLOW_PAID=true` | — | **Paid** |

Crawl: `CRAWL_ENGINE=trafilatura` (mặc định) / `crawl4ai`; `CRAWL_RESPECT_ROBOTS=true` (không tắt ở production); `CRAWL_CACHE_TTL_DAYS=30`.

---

# 6. Sinh ảnh & Asset

| Biến | Mặc định |
|---|---|
| `IMAGE_GEN_CHAIN` | `local_sd,gemini_image` |
| `ASSET_CHAIN` | `pexels,pixabay,unsplash` |

| Provider | Kích hoạt bởi | Phí |
|---|---|---|
| `local_sd` | `SD_URL` (ComfyUI/A1111) hoặc `SD_MODEL=flux1-schnell` + GPU | Free |
| `gemini_image` | `GEMINI_API_KEY` | Free tier |
| `pexels` | `PEXELS_API_KEY` (free đăng ký) | Free |
| `pixabay` | `PIXABAY_API_KEY` | Free |
| `unsplash` | `UNSPLASH_ACCESS_KEY` | Free (50 req/h demo) |

Không có key stock nào → Asset Worker chỉ dùng thư viện nội bộ + ảnh AI local (pipeline vẫn chạy).

---

# 7. Storage

| Biến | Mặc định |
|---|---|
| `STORAGE_PROVIDER` | `minio` (`s3` khi có AWS credentials) |
| `MINIO_URL` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | compose nội bộ |
| `S3_BUCKET` / `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` | — |

Cùng adapter, cùng path layout (ARCHITECTURE.md §6) — chuyển MinIO → S3 chỉ đổi env.

---

# 8. Publish

| Biến | Mặc định |
|---|---|
| `PUBLISH_PLATFORMS` | `download` |

| Nền tảng | Kích hoạt bởi | Ghi chú |
|---|---|---|
| `download` | luôn có | MP4 + metadata copy sẵn |
| `youtube` | `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET` (OAuth flow trong UI) | quota free 10k units/ngày |
| `tiktok` | `TIKTOK_CLIENT_KEY` + `TIKTOK_CLIENT_SECRET` (app đã được duyệt) | fallback `download` khi chưa duyệt |
| `facebook` | `FACEBOOK_APP_ID` + `FACEBOOK_APP_SECRET` | như trên |
| `linkedin` | `LINKEDIN_CLIENT_ID` + `LINKEDIN_CLIENT_SECRET` | |

`PUBLISH_AI_DISCLOSURE=true` (mặc định, không nên tắt): bật cờ khai báo AI-generated content ở nền tảng hỗ trợ.

---

# 9. Notification & Monitoring

| Biến | Kích hoạt | Ghi chú |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | có token | thông báo FAIL / cost cap / DLQ |
| `SMTP_URL` | có URL | email notification |
| `SENTRY_DSN` | có DSN | self-host Sentry/GlitchTip |
| `LANGFUSE_HOST` + keys | có host | LLM tracing self-host |

---

# 10. Worker & Render

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `RENDER_WORKER_REPLICAS` | `1` | compose scale |
| `RENDER_CONCURRENCY` | `1` | job đồng thời / worker |
| `RENDER_CRF` | `20` | chất lượng encode |
| `RENDER_CACHE_TTL_DAYS` | `30` | dọn cache scene |
| `VOICE_WORKER_REPLICAS` | `1` | |

---

# 11. Ví dụ

## 11.1 `.env.local` — chạy 0đ, không API key

```env
APP_ENV=development
ALLOW_PAID=false
DAILY_COST_CAP=0
DEFAULT_LANGUAGE=vi
MODE1_AUTOPUBLISH=off

JWT_SECRET=change-me
FERNET_MASTER_KEY=change-me
DATABASE_URL=postgresql://app:app@postgres:5432/app

# LLM: chỉ local
LLM_CHAIN_CHEAP=ollama
LLM_CHAIN_STRONG=ollama
OLLAMA_MODEL_CHEAP=qwen2.5:14b-instruct
OLLAMA_MODEL_STRONG=qwen2.5:14b-instruct
EMBEDDING_CHAIN=bge_m3_local

# TTS: edge-tts (free)
TTS_CHAIN=edge_tts

# Search: SearXNG self-host
SEARCH_CHAIN=searxng
SEARXNG_URL=http://searxng:8080

# Asset: thư viện nội bộ + SD local (nếu có GPU)
ASSET_CHAIN=
IMAGE_GEN_CHAIN=local_sd

STORAGE_PROVIDER=minio
PUBLISH_PLATFORMS=download
```

## 11.2 `.env.production` — free tier + YouTube, sẵn sàng bật paid

```env
APP_ENV=production
ALLOW_PAID=false            # bật true khi quyết định đầu tư
DAILY_COST_CAP=5
DEFAULT_LANGUAGE=vi
MODE1_AUTOPUBLISH=pass_only
NATS_URL=nats://nats:4222

LLM_CHAIN_CHEAP=ollama,gemini,openrouter_free
LLM_CHAIN_STRONG=gemini,groq,openrouter_free
GEMINI_API_KEY=...
GROQ_API_KEY=...
OPENROUTER_API_KEY=...

TTS_CHAIN=edge_tts,local_tts
TTS_LOCAL_MODEL=vixtts

SEARCH_CHAIN=searxng,tavily,brave
TAVILY_API_KEY=...
BRAVE_API_KEY=...

ASSET_CHAIN=pexels,pixabay
PEXELS_API_KEY=...
PIXABAY_API_KEY=...

PUBLISH_PLATFORMS=download,youtube
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...

TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

RENDER_WORKER_REPLICAS=2
```

## 11.3 Nâng cấp lên trả phí (khi hệ thống đã ổn định)

Chỉ đổi env — không sửa code:

```env
ALLOW_PAID=true
DAILY_COST_CAP=10
LLM_CHAIN_STRONG=gemini,openrouter_paid,groq
OPENROUTER_PAID_MODEL=anthropic/claude-sonnet-5
TTS_CHAIN=fpt,edge_tts,local_tts
FPT_API_KEY=...
# hoặc thay/thêm elevenlabs nếu ưu tiên giọng đa ngôn ngữ chất lượng cao nhất chain:
# TTS_CHAIN=elevenlabs,fpt,edge_tts,local_tts
# ELEVENLABS_API_KEY=...
```
