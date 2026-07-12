# Anti-pattern: Direct Provider Call

**Problem:** calling an external provider's SDK/HTTP API directly from a pipeline node or business-logic service instead of going through an adapter.

**Symptoms**
- `import openai` / `requests.post("https://api...")` inside `app/pipeline/nodes/` or `app/services/`.
- Env var (`GEMINI_API_KEY`, etc.) read directly in business logic instead of via `ProviderSettings`.
- A "just this once, it's simple" provider integration that skips the base-class + registry pattern.

**Impact:** breaks local-first/env-driven activation (a hardcoded provider can't fail over or be swapped via env), breaks cost tracking (usage isn't logged uniformly), breaks `ALLOW_PAID` enforcement (no central gate to check), makes testing require real network calls.

**Correct Solution:** [patterns/provider-adapter.md](../patterns/provider-adapter.md) — base class + `@register_{capability}` decorator, every capability access goes through the router's chain-based `call()`.

**Detection:** grep for provider SDK imports or raw `httpx`/`requests` calls outside `app/adapters/`.

**How to Avoid:** Architect and Backend Engineer agents reject any PR introducing a new external capability without an adapter — no exceptions for "just a quick test," since quick tests have a way of becoming permanent.
