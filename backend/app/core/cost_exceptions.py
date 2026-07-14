"""Cost-domain exceptions (Task 3-5).

DailyCostCapExceeded: raised when accumulated daily spend hits DAILY_COST_CAP.
Pipeline catches this at node boundary (BR-2), sets FAILED(reason=cost_cap)
and emits cost.cap_reached — then stops starting new nodes.
"""

from __future__ import annotations


class DailyCostCapExceeded(Exception):
    def __init__(self, current: float, limit: float, last_provider: str = "") -> None:
        self.current = current
        self.limit = limit
        self.last_provider = last_provider
        super().__init__(
            f"daily cost cap exceeded: {current:.4f} >= {limit:.4f} USD (last: {last_provider})"
        )
