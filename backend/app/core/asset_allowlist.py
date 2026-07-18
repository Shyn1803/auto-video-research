"""Stock-CDN domain allowlist (Task 5-3, FR-20 / SSRF defense-in-depth).

Single source of truth for "which raw ``url`` hosts may ever appear in a
Scene JSON `AssetRef.url`" -- per docs/specs/scene-json-schema.md §3.7:
"`url` trực tiếp chỉ cho phép domain allowlist (Pexels/Pixabay CDN) ... Render
Worker không bao giờ fetch URL ngoài". Used by:

  - ``AssetService.fetch_stock`` (defense-in-depth before ever issuing an
    outbound request for a user-selected stock result).
  - ``scene_validator.validate_scene`` (rejects a raw, non-allowlisted URL
    submitted through ``PUT /scenes/{id}`` with 422 -- AC4).

Adding a new stock provider means adding its CDN host here, not scattering
domain checks across call sites.
"""

from __future__ import annotations

from urllib.parse import urlsplit

ALLOWED_ASSET_HOSTS: frozenset[str] = frozenset(
    {
        "images.pexels.com",
        "pexels.com",
        "www.pexels.com",
        "pixabay.com",
        "cdn.pixabay.com",
        "images.unsplash.com",
    }
)


def is_allowed_asset_host(url: str) -> bool:
    """Return True when *url*'s host is an allowlisted stock CDN domain."""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    return host in ALLOWED_ASSET_HOSTS
