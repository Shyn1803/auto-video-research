"""arXiv connector -- free, no key required (Task 4-3 Step 2).

arXiv's public API returns an Atom feed -- parsed with the stdlib
``xml.etree`` (no extra dependency needed for this small, well-known shape).
"""

from __future__ import annotations

import logging
from xml.etree import ElementTree as ET

import httpx

from app.adapters.base import ProviderError, ProviderSettings, SearchAdapter
from app.adapters.registry import register_search

logger = logging.getLogger("avr.search.arxiv")

_API_URL = "http://export.arxiv.org/api/query"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


@register_search("arxiv")
class ArxivSearch(SearchAdapter):
    """arXiv paper search -- free, no API key."""

    name: str = "arxiv"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)

    async def available(self) -> bool:
        return True

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "vi"
    ) -> list[dict[str, str]]:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    _API_URL,
                    params={
                        "search_query": f"all:{query}",
                        "start": 0,
                        "max_results": max_results,
                    },
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(
                f"arxiv HTTP {status}: {exc}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"arxiv connection error: {exc}", retryable=True) from exc

        return parse_arxiv_feed(resp.text)


def parse_arxiv_feed(xml_text: str) -> list[dict[str, str]]:
    """Parse an arXiv Atom feed into result dicts (testable without HTTP)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ProviderError(f"arxiv: malformed Atom feed: {exc}", retryable=False) from exc

    results: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        title_el = entry.find("atom:title", _ATOM_NS)
        summary_el = entry.find("atom:summary", _ATOM_NS)
        id_el = entry.find("atom:id", _ATOM_NS)
        published_el = entry.find("atom:published", _ATOM_NS)
        author_els = entry.findall("atom:author/atom:name", _ATOM_NS)

        results.append(
            {
                "title": (title_el.text or "").strip() if title_el is not None else "",
                "url": (id_el.text or "").strip() if id_el is not None else "",
                "snippet": (summary_el.text or "").strip() if summary_el is not None else "",
                "published_at": (published_el.text or "").strip() if published_el is not None else "",
                "author": ", ".join(a.text or "" for a in author_els),
            }
        )
    return results
