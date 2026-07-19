"""Anti-repetition post-pass — Step 7 of 4-6 (BR-9).

Applied AFTER classification on every scene, purely deterministic.
Rules (from video-taste.md §4.2):
- No more than 2 consecutive scenes of the same layout class.
- No class exceeds 40% of total scenes (Hero/TextFocus exception: ≤2 scenes).
- Videos ≥8 scenes must use ≥4 distinct classes.
- Non-compliant: emit a warning only — no auto-fix loop (explicit BR-9).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("avr.layout_engine.post_pass")


def check_repetition(
    classifications: list[dict[str, Any]],
    *,
    total_scenes: int,
) -> list[str]:
    """Return a list of human-readable warnings (empty = compliant).

    classifications is the list returned by classify_tree().
    """
    warnings: list[str] = []
    layouts = [c["layout"] for c in classifications]

    # Rule 1: no more than 2 consecutive same-class scenes.
    consecutive = 1
    for i in range(1, len(layouts)):
        if layouts[i] == layouts[i - 1]:
            consecutive += 1
            if consecutive > 2:
                warnings.append(
                    f"Consecutive repetition: {layouts[i]} appears {consecutive} "
                    f"times in a row starting at scene {i + 1 - consecutive + 1} "
                    f"(BR-9: max 2)."
                )
        else:
            consecutive = 1

    # Rule 2: no class > 40% total (Hero/TextFocus exempted).
    exempt = {"Hero", "TextFocus"}
    from collections import Counter
    dist = Counter(layouts)
    threshold = max(1, int(total_scenes * 0.4))
    for cls, count in dist.items():
        if cls not in exempt and count > threshold:
            warnings.append(
                f"Layout '{cls}' appears {count} times ({count/total_scenes:.0%}) "
                f"across {total_scenes} scenes (BR-9: max 40% unless Hero/TextFocus)."
            )

    # Rule 3: ≥8 scenes → ≥4 distinct classes.
    if total_scenes >= 8:
        distinct = len(dist)
        if distinct < 4:
            warnings.append(
                f"Video has {total_scenes} scenes but only {distinct} distinct "
                f"layout classes (BR-9: min 4 for ≥8 scenes)."
            )

    for w in warnings:
        logger.warning("post-pass violation: %s", w)
    return warnings
