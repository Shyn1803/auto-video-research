"""BR-2 narration-validation Step 2 — 10 fixture pairs."""

from __future__ import annotations

import pytest

from app.pipeline.nodes.storyboard.validate import validate_narration_matches_voiceover


# ---------- helpers ----------

class _S:
    def __init__(self, num: int, narration_text: str):
        self.scene_number = num
        self.narration_text = narration_text
        self.components = [{"kind": "body", "summary": "body"}]


def _scenes(*texts: str, start: int = 1):
    return [_S(start + i, t) for i, t in enumerate(texts)]


# ---------- fixtures (10 pairs per task spec) ----------
VO_01 = "Mo dau gioi thieu chu de chinh. Giai thich chi tiet noi dung phan tich."
VO_02_FAIL = "Mo dau gioi thieu chu de."
VO_03 = "  Mo dau  gioi thieu  chu de.  "
VO_04_FAIL = "Mo dau gioi thieu chu de. Giai thich chi tiet noi dung phan tich. Phan ket luan."
VO_05 = "Mo dau gioi thieu chu de chinh."
VO_06 = "Giói thịu chủ đè."  # NFD form
VO_07_FAIL = "MO DAU GIOI THIEU CHU DE."
VO_08 = "Mo dau-do gioi thieu chu-de chinh."
VO_09 = ""
VO_10_FAIL = "Giai thich chi tiet noi dung phan tich. Mo dau gioi thieu chu de chinh."


# ---------- pairs ----------
PAIRS = [
    # 1. success — two scenes, exact match
    ("pair01 OK", _scenes("Mo dau gioi thieu chu de chinh.", "Giai thich chi tiet noi dung phan tich."), VO_01, False),
    # 2. failure — voiceover truncated
    ("pair02 FAIL", _scenes("Mo dau gioi thieu chu de chinh.", "Giai thich chi tiet noi dung phan tich."), VO_02_FAIL, True),
    # 3. boundary — leading/trailing whitespace normalised out
    ("pair03 OK", _scenes("Mo dau gioi thieu chu de chinh."), VO_03, False),
    # 4. failure — extra scene text vs voiceover
    ("pair04 FAIL", _scenes("Mo dau gioi thieu chu de chinh.", "Giai thich chi tiet noi dung phan tich."), VO_04_FAIL, True),
    # 5. success — single scene
    ("pair05 OK", _scenes("Mo dau gioi thieu chu de chinh."), VO_05, False),
    # 6. boundary — NFD normalisation
    ("pair06 OK", _scenes("Giói thịu chủ đè."), VO_06, False),
    # 7. failure — case mismatch
    ("pair07 FAIL", _scenes("Mo dau gioi thieu chu de chinh."), VO_07_FAIL, True),
    # 8. success — dash/hyphen preserved
    ("pair08 OK", _scenes("Mo dau-do gioi thieu chu-de chinh."), VO_08, False),
    # 9. boundary — empty voiceover against empty narration
    ("pair09 OK", _scenes(""), VO_09, False),
    # 10. failure — scene order wrong
    ("pair10 FAIL", _scenes("Mo dau gioi thieu chu de chinh.", "Giai thich chi tiet noi dung phan tich."), VO_10_FAIL, True),
]


@pytest.mark.parametrize("label,scenes,voiceover,expect_error", PAIRS, ids=lambda p: p[0])
def test_narration_br2(label, scenes, voiceover, expect_error):
    """BR-2: mismatch is an engine bug, never ship with a warning."""
    errors = validate_narration_matches_voiceover(scenes, voiceover, strict=True)
    if expect_error:
        assert errors, f"expected mismatch error for {label}"
    else:
        assert not errors, f"unexpected error for {label}: {errors}"

