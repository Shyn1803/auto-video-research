# Pattern: Provider Adapter

**Problem:** every external capability (LLM, TTS, search, image-gen, asset, storage, publish) needs a local-first default with paid options that activate purely via env, with automatic failover — without scattering provider-specific logic through business code.

**Solution:** one abstract base class per capability + a registry decorator. From `docs/dev-guide.md` §3:

```python
# app/adapters/tts/base.py
class TTSAdapter(ABC):
    name: str
    is_paid: bool = False
    @abstractmethod
    async def available(self) -> bool: ...        # key exists / service reachable
    @abstractmethod
    async def synthesize(self, req: TTSRequest) -> TTSResult: ...  # raise ProviderError

# app/adapters/tts/fpt.py — adding a provider is ONLY this
@register_tts("fpt")
class FptTTS(TTSAdapter):
    name, is_paid = "fpt", True
    async def available(self): return bool(await get_key("fpt"))
    async def synthesize(self, req): ...
```

**Rules (non-negotiable):**
1. Adapter never reads env directly — receives config via `ProviderSettings`.
2. Adapter never wraps exceptions itself into anything but `ProviderError(retryable: bool)` — the router decides failover.
3. Usage/cost logging (`llm_usage`, key usage counters) happens in the router, never the adapter.
4. Ships with a unit test: `available()` in each state, `synthesize`/equivalent HTTP-mocked via respx.
5. New provider name added to `docs/CONFIGURATION.md`'s provider table in the same PR.

**When to use:** any new external capability, always. There is no "just call the SDK directly this once" exception — see [anti-patterns/direct-provider-call.md](../anti-patterns/direct-provider-call.md).

**Developing/testing an adapter from a network-restricted agent sandbox** (can't reach the real provider API): see [sandboxed-agent-network-fallback.md](sandboxed-agent-network-fallback.md) — prefer an offline-bundled binary where one exists, or a standalone local-run script for genuinely network-only paid providers. This never changes the shipped adapter's shape, only how you exercise it during dev.

**Router logic (the failover chain, ARCHITECTURE.md §2.2):**
```
for provider in chain(tier):
    if not provider.available(): continue
    try: return provider.call(...)          # + log usage
    except QuotaError: rotate_key(provider) or next
    except TimeoutError, 5xx: next           # + event provider_failover
raise AllProvidersFailed
```
