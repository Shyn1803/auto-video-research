# Context: Project Overview

**Full detail:** `docs/SRS.md` §1-2. This is a summary + pointer, not a fork.

**What it is:** AI Content Research & Video Automation Platform — a Vietnamese-language "AI Video Production Studio." Researches a topic, fact-checks claims, writes a script, storyboards it, renders via Remotion, publishes to social platforms. AI assists every step; a human can intervene at any step.

**Two operating modes (both in scope, not MVP-vs-later):**
- **Mode 1 — Daily AI News** (full-auto with gates): Scheduler-triggered, runs Research→Ranking→FactCheck(gate)→Outline→Script→Storyboard→Render→Publish. Publish gate configurable via `MODE1_AUTOPUBLISH`: `off` (default, always wait for approval) / `pass_only` (auto-publish only FactCheck=PASS) / `on` (needs ≥95% historical accuracy shown on dashboard).
- **Mode 2 — Interactive Project**: user enters a topic, reviews/edits at every step, approves, can go back, versions everything.

**Core commitment (SRS §1.2, repeated everywhere):** local-first. 0 API keys → full pipeline still runs (Ollama, edge-tts, SearXNG, local Stable Diffusion, MinIO). Paid providers activate purely via env API key + `ALLOW_PAID=true` — no code change, no redeploy.

**Scope stance:** this is a full production/scale-ready spec, not an MVP cut down in scope. `docs/plan.md` is one continuous 18-week timeline to Release v1.0 — "Phase" labels are delivery sequencing only.

**Personas:** Admin (users/RBAC, prompts, scheduler, API keys/provider activation, queue/worker health, audit) and Content Creator (create project, research, script, storyboard/scene edit, render, publish, analytics).

See also: [business-domain.md](business-domain.md), [architecture.md](architecture.md), `docs/glossary.md`.
