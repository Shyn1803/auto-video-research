"""Demo LLM adapter — the copy-paste template for all future LLM providers.

Adding a real provider: copy this file, rename the class, implement the
``call_structured`` method (or delegate to the real SDK), register with
``@register_llm("the_provider_name")``.  That is all.
"""

from __future__ import annotations

from app.adapters.base import LLMAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm


@register_llm("demo")
class DemoLLM(LLMAdapter):
    """Minimal LLM adapter: echo back the prompt as a JSON dict.

    This adapter is the canonical template — every new LLM provider adapter
    follows this shape.  Real adapters replace the echo stub with an actual
    provider SDK call and return the parsed JSON.
    """

    name: str = "demo"
    is_paid: bool = False  # free / local default is cost-safe

    async def available(self) -> bool:
        """Always available (no external dependency)."""
        return True

    async def call_structured(
        self,
        prompt: str,
        schema: dict[str, object],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict[str, object]:
        """Return a stub response based on *prompt* and *schema* keys.

        In a real adapter this would call the provider API and parse the
        returned JSON to ensure it matches *schema*.
        """
        if not self.settings.api_key:
            # Even a demo adapter reports config failure via ProviderError.
            raise ProviderError(
                "demo adapter: no api_key provided (set a dummy value for testing).",
                retryable=False,
            )

        # Build a stub response keyed by the top-level schema keys.
        output: dict[str, object] = {}
        for key in schema:
            output[key] = f"[demo:{prompt[:32]}]"

        return output
