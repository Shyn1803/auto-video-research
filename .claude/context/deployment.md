# Context: Deployment

**Full detail:** `docs/ARCHITECTURE.md` §10, `docs/CONFIGURATION.md`, `docs/runbook.md`.

**Phase 1-2:** single docker-compose stack — `frontend, api, render-worker (replicas), voice-worker, postgres, nats, minio, ollama, searxng, prometheus, grafana, langfuse`. One GPU host (Ollama/local TTS/SD) optionally plus a CPU host for render workers. Same compose file for dev/prod, differing only by `.env`.

**Phase 3 (load-driven only, not scheduled by default):** Option A (preferred, simpler) — multiple docker-compose hosts, NATS cluster of 3 nodes, workers join via NATS URL, no Kubernetes needed. Option B (heavy load) — Kubernetes + KEDA autoscaling workers on NATS queue depth. PostgreSQL gets pgbouncer + read replica if needed; backup = daily dump + WAL archive; MinIO replicates to a second host.

**Provider activation is entirely env-driven** — `.env` alone determines which providers are active; see `docs/CONFIGURATION.md` §11 for three worked examples (`.env.local` 0-cost, `.env.production` free-tier+YouTube, paid upgrade diff). Never gate provider activation behind a code change.

**Network exposure:** only API and Frontend are internet-facing; NATS/PostgreSQL/MinIO/Ollama stay on the internal docker network.

**Status:** no compose files, Dockerfiles, or actual deployment exist yet — this is the target architecture. See [devops-engineer agent](../agents/devops-engineer.md).
