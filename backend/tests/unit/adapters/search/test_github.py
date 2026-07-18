"""Task 4-3 Step 2 -- GitHub connector."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.adapters.base import ProviderError
from app.adapters.search.github import GitHubSearch, parse_github_response

_RESPONSE = {
    "items": [
        {
            "full_name": "org/cool-repo",
            "html_url": "https://github.com/org/cool-repo",
            "description": "A cool AI repo",
            "owner": {"login": "org"},
            "updated_at": "2024-01-01T00:00:00Z",
        }
    ]
}


def test_parse_github_response():
    results = parse_github_response(_RESPONSE)
    assert len(results) == 1
    assert results[0]["title"] == "org/cool-repo"
    assert results[0]["author"] == "org"


@pytest.mark.asyncio
@respx.mock
async def test_search_works_unauthenticated():
    respx.get("https://api.github.com/search/repositories").mock(
        return_value=Response(200, json=_RESPONSE)
    )
    adapter = GitHubSearch()
    assert await adapter.available() is True
    results = await adapter.search("ai video", max_results=5)
    assert len(results) == 1


@pytest.mark.asyncio
@respx.mock
async def test_403_rate_limit_is_retryable():
    respx.get("https://api.github.com/search/repositories").mock(return_value=Response(403))
    adapter = GitHubSearch()
    with pytest.raises(ProviderError) as exc_info:
        await adapter.search("x")
    assert exc_info.value.retryable is True
