"""Domain exceptions for provider chain operations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderFailure:
    """Single provider failure record — appears inside AllProvidersFailed.failures."""

    provider: str = ""
    reason: str = ""
    retryable: bool = False


class AllProvidersFailed(Exception):
    """Raised when every provider in the chain has been exhausted or rejected."""

    def __init__(
        self,
        capability: str = "",
        chain: list[str] | None = None,
        failures: list[ProviderFailure] | None = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(capability)
        self.capability = capability
        self.chain: list[str] = chain or []
        self.failures: list[ProviderFailure] = failures or []
        self.correlation_id = correlation_id

    def __str__(self) -> str:
        parts = [f"capability={self.capability}"]
        if self.chain:
            parts.append(f"chain={','.join(self.chain)}")
        if self.failures:
            fail_str = "; ".join(f"{f.provider}({f.reason})" for f in self.failures)
            parts.append(f"failures=[{fail_str}]")
        return f"AllProvidersFailed({', '.join(parts)})"
