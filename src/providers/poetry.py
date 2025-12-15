"""Poetry provider for fetching and displaying Chinese poetry.

Fetches poetry from 今日诗词 API with hourly caching and local fallback.
"""

import logging
from typing import TypedDict

import httpx

from ..config import Config
from .base import BaseContentProvider

logger = logging.getLogger(__name__)


class Poetry(TypedDict):
    """Poetry data structure."""

    content: str  # Poetry text
    author: str  # Poet name
    title: str  # Poem title


# Local fallback poetry
FALLBACK_POETRY: list[Poetry] = [
    {
        "content": "春眠不觉晓，处处闻啼鸟。\\n夜来风雨声，花落知多少。",
        "author": "孟浩然",
        "title": "春晓",
    },
    {
        "content": "床前明月光，疑是地上霜。\\n举头望明月，低头思故乡。",
        "author": "李白",
        "title": "静夜思",
    },
    {
        "content": "海内存知己，天涯若比邻。",
        "author": "王勃",
        "title": "送杜少府之任蜀州",
    },
    {
        "content": "人生自古谁无死，留取丹心照汗青。",
        "author": "文天祥",
        "title": "过零丁洋",
    },
    {
        "content": "会当凌绝顶，一览众山小。",
        "author": "杜甫",
        "title": "望岳",
    },
]


class PoetryProvider(BaseContentProvider):
    """Provider for fetching and caching Chinese poetry."""

    def __init__(self):
        """Initialize poetry provider with caching and fallback."""
        super().__init__(
            cache_filename="poetry_cache.json",
            fallback_data=FALLBACK_POETRY,
            content_type="poetry",
            cache_hours=Config.display.quote_cache_hours,  # Reuse quote cache config
        )

    async def get_poetry(self, client: httpx.AsyncClient | None = None) -> Poetry:
        """Get current poetry (cached or fresh).

        Args:
            client: Optional Async HTTP client

        Returns:
            Poetry dictionary with content, author, and title
        """
        return await self.get_content(client)

    async def _fetch_content(self, client: httpx.AsyncClient | None = None) -> Poetry:
        """Fetch Chinese poetry from custom poetry API.

        Args:
            client: Optional Async HTTP client

        Returns:
            Poetry dictionary

        Raises:
            httpx.HTTPError: If HTTP request fails
            ValueError: If API response is invalid or URL not configured
        """
        api_url = Config.display.poetry_api_url

        if not api_url:
            raise ValueError(
                "POETRY_API_URL not configured. Please set it in .env file to use poetry mode."
            )

        return await self._fetch_from_poetry_api(api_url, client)

    async def _fetch_from_poetry_api(
        self, url: str, client: httpx.AsyncClient | None = None
    ) -> Poetry:
        """Fetch poetry from custom API.

        Expected response format:
        {
            "id": 210993,
            "title": "靜夜思",
            "author": {"id": 12214, "name": "釋鹹潤"},
            "content": ["牀前看月光，疑是地上霜。", "舉頭望明月，低头思故乡。"],
            "dynasty": {"id": 6, "name": "唐", ...},
            "type": {"id": 11, "name": "五言絕句", ...}
        }

        Args:
            url: Custom API URL
            client: Optional Async HTTP client

        Returns:
            Poetry dictionary
        """
        if client:
            response = await client.get(url, timeout=10.0)
        else:
            async with httpx.AsyncClient(timeout=10.0) as new_client:
                response = await new_client.get(url)

        response.raise_for_status()
        data = response.json()

        # Extract author name (handle both dict and string)
        author = data.get("author", {})
        if isinstance(author, dict):
            author_name = author.get("name", "Unknown")
        else:
            author_name = str(author) if author else "Unknown"

        # Format content - join list into string with newlines
        content = data.get("content", [])
        if isinstance(content, list):
            content_str = "\\n".join(content)
        else:
            content_str = str(content)

        # Build title
        poem_title = data.get("title", "")

        return {
            "content": content_str,
            "author": author_name,
            "title": poem_title,
        }


# Singleton instance
_poetry_provider = None


async def get_poetry(client: httpx.AsyncClient | None = None) -> Poetry:
    """Get current poetry (module-level function).

    Args:
        client: Optional Async HTTP client

    Returns:
        Poetry dictionary
    """
    global _poetry_provider
    if _poetry_provider is None:
        _poetry_provider = PoetryProvider()
    return await _poetry_provider.get_poetry(client)
