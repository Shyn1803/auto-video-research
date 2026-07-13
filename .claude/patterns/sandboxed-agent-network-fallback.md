# Pattern: Sandboxed-Agent Network Fallback

**Problem:** a coding agent's own sandbox (Claude Code's bash tool, CI runner, or any restricted dev shell) often has a narrow network allowlist (e.g. only `pypi.org`, `registry.npmjs.org`, `github.com`) and a hard per-command timeout (e.g. 45s, no background process surviving between commands). This is a *dev-time tooling constraint*, separate from the production system's own provider-chain design (`docs/CONFIGURATION.md` §3-8, [provider-adapter.md](provider-adapter.md)) — but it directly blocks the agent from exercising TTS/render/asset code paths locally while building or debugging them. Source: a prior TikTok-video pipeline built end-to-end in exactly this kind of sandbox (see project handoff notes referenced in [memory/project-memory.md](../memory/project-memory.md)).

**Solution — three sub-patterns, pick per situation:**

### 1. Prefer offline-bundled binaries over live API calls when one exists
Many capabilities have a pip/npm package that bundles the actual binary/model instead of calling a hosted API:
- TTS: `espeakng-loader` (bundles `libespeak-ng.so` + language data, incl. Vietnamese) + call `espeak_Initialize`/`espeak_Synth` directly via ctypes (`pyttsx3.drivers._espeak`) — **not** `py-espeak-ng`, which shells out to an `espeak-ng` CLI binary the sandbox doesn't have.
- Headless Chrome for Remotion render: `@sparticuz/chromium` (npm) ships a compressed Chromium binary that self-extracts locally — point Remotion at it with `--browser-executable=<path from chromium.executablePath()>` + `--gl=angle`, no download needed.
- General rule: if `apt-get install` would be needed, look for a pip/npm package that vendors the binary instead — sandboxes rarely have root/apt.

This maps onto the existing `local_tts` provider slot in `TTS_CHAIN` (`docs/CONFIGURATION.md` §4) — it's a legitimate *free, local* provider, not just a dev workaround.

### 2. Network-only paid APIs → split into a standalone local-run script
When a capability genuinely requires an outbound call to a paid provider the sandbox can't reach (ElevenLabs TTS, etc.), don't try to route around the sandbox — write a **self-contained script using only stdlib (`urllib`) or already-allowlisted packages**, with no extra install steps, that the user runs on their own machine with real network access. The user runs it and feeds the output (audio files + a `timeline.json` measuring real durations) back into the project.

Reuse this for every paid provider that hits the same wall — one script template, not a bespoke one-off each time. This is the same failover *contract* as the adapter pattern ([provider-adapter.md](provider-adapter.md)) — `ElevenLabsTTS` still gets a real adapter in `app/adapters/tts/elevenlabs.py` for production; the standalone script is only a **local dev/debug aid** for exercising it from inside a network-restricted agent sandbox, never a substitute for the adapter in shipped code.

### 3. Time-limited shell commands → chunk + concat, never one long-running command
If a single command (e.g. `renderMedia()` for a whole video) would exceed the sandbox's per-command timeout and can't run in the background across commands:
- Split by a deterministic unit (frame range, batch of N items) sized to comfortably fit one command.
- Run each chunk as its own command, writing to `chunk{N}.mp4`/equivalent.
- Concatenate losslessly at the end: `ffmpeg -f concat -safe 0 -i concat.txt -c copy final.mp4`. Audio stays in sync because Remotion renders each chunk at its absolute frame position in the composition, not relative to the chunk — `-c copy` concat doesn't need to touch timestamps.
- A `renderInChunks(totalFrames, chunkSize)` helper that emits the chunk render commands + the final concat command is worth writing once and reusing for every video, instead of computing chunk boundaries by hand each time.

This is a *dev/debug-loop* concern only. The production Render Worker (story 6.2/9.2) is a long-lived process, not a 45s sandbox command — it doesn't need chunking, only the already-documented `bundle()`-once-cache-`serveUrl` discipline ([remotion-integration.md](../../docs/specs/remotion-integration.md) §2.5, epic-06 BR-6). Don't let a sandbox workaround leak into the real render-worker design.

**Audio↔visual sync contract (applies regardless of sandbox):** never estimate scene/line duration from word count. Measure the real rendered audio duration (sample count / sample rate, or `ffprobe`) per line, accumulate `start`/`end`, and write a `timeline.json` that every downstream step (captions, Sequence `from`/`durationInFrames`) reads from — never hardcode a second value in component code. This is the same principle as Motion Planner PASS-2 re-resolving `motion_plan` from real TTS word timestamps ([remotion-integration.md](../../docs/specs/remotion-integration.md) §4) — a draft/estimated timing pass is fine, but the final artifact must be built from measured durations.

**When to use:** any time you (the coding agent) need to exercise TTS, render, or another network/binary-heavy capability from inside this sandbox during development — not a production runtime design. Production behavior stays defined by `docs/CONFIGURATION.md` and [provider-adapter.md](provider-adapter.md).

**See also:** [provider-adapter.md](provider-adapter.md), [remotion-integration.md](../../docs/specs/remotion-integration.md) §2.5/§4, [context/build-process.md](../context/build-process.md).
