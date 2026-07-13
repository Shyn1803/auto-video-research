"""Canonical Scene JSON cache-key tests."""

from app.schemas.scene import canonical_hash


def test_canonical_hash_ignores_scene_order_and_scene_number() -> None:
    """AC-3: reordering a project does not invalidate per-content cache identity."""

    first = {
        "scenes": [
            {"scene_number": 1, "content": "Một"},
            {"scene_number": 2, "content": "Hai"},
        ]
    }
    reordered = {
        "scenes": [
            {"scene_number": 99, "content": "Hai"},
            {"scene_number": 42, "content": "Một"},
        ]
    }

    assert canonical_hash(first) == canonical_hash(reordered)


def test_canonical_hash_changes_when_content_changes() -> None:
    """AC-3: changing even one content character produces a new key."""

    first = {"scene_number": 1, "content": "Một"}
    changed = {"scene_number": 1, "content": "Mốt"}

    assert canonical_hash(first) != canonical_hash(changed)
