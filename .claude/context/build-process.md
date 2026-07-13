# Context: Build Process

**Full detail:** `docs/dev-guide.md` §2. **Status: intent from docs, not yet executable** — no Makefile, docker-compose files, or code exist yet to actually run these commands.

**Planned dev loop:**
```bash
cp .env.example .env             # default = 0 API keys, local-first
make up                          # docker compose: postgres, minio, ollama, searxng
make migrate                     # alembic upgrade head + seed
make ollama-pull                 # pull qwen2.5:14b-instruct once
make backend                     # uvicorn --reload → localhost:8000/docs
make frontend                    # next dev → localhost:3000
make test                        # pytest + vitest
npx skills add remotion-dev/skills   # inside packages/remotion-templates/
```

**Scene schema regeneration (critical, easy to forget):** editing `app/schemas/scene.py` requires running `make gen-scene-schema` to regenerate the JSON Schema export and the Zod schema in `packages/remotion-templates/src/schema.ts`. Per dev-guide.md, CI should fail if this is skipped — but no CI exists yet to actually enforce it. Until CI exists, this is a manual discipline point for Reviewer agent to check.

**API client generation:** `make gen-api-client` — regenerates the frontend's OpenAPI-derived TypeScript client. Never hand-write a duplicate interface instead of running this.

**No GPU dev fallback:** set `OLLAMA_MODEL_CHEAP=qwen2.5:7b-instruct` or configure `GEMINI_API_KEY` for faster dev iteration. All unit tests must run without Ollama/GPU (mocked).

**Coding-agent sandbox network/time limits:** if you (the agent) are developing/debugging inside a restricted sandbox (narrow network allowlist, hard per-command timeout, no background process across commands) rather than the real dev-compose stack, see [patterns/sandboxed-agent-network-fallback.md](../patterns/sandboxed-agent-network-fallback.md) before assuming a capability (TTS, Remotion render) is unreachable — this is a dev-tooling constraint, not a production design change.

TODO once real: replace this file's command list with verified, tested commands; note actual `Makefile` target names if they diverge from the plan.
