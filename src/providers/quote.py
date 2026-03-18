"""Quote provider for fetching and displaying famous quotes.

Fetches quotes from Quotable API with hourly caching and local fallback.
"""

import logging
from typing import TypedDict

import httpx

from ..config import Config
from .base import BaseContentProvider

logger = logging.getLogger(__name__)


class Quote(TypedDict):
    """Quote data structure."""

    content: str  # Quote text
    author: str  # Author name
    source: str  # Citation source (optional)


# Local fallback quotes
FALLBACK_QUOTES: list[Quote] = [
    {
        "content": "Stay hungry, stay foolish.",
        "author": "Steve Jobs",
        "source": "Stanford Commencement 2005",
    },
    {
        "content": "The only way to do great work is to love what you do.",
        "author": "Steve Jobs",
        "source": "",
    },
    {
        "content": "Life is what happens when you're busy making other plans.",
        "author": "John Lennon",
        "source": "",
    },
    {
        "content": "In the middle of difficulty lies opportunity.",
        "author": "Albert Einstein",
        "source": "",
    },
    {
        "content": "The future belongs to those who believe in the beauty of their dreams.",
        "author": "Eleanor Roosevelt",
        "source": "",
    },
]


class QuoteProvider(BaseContentProvider):
    """Provider for fetching and caching famous quotes."""

    def __init__(self):
        """Initialize quote provider with caching and fallback."""
        super().__init__(
            cache_filename="quote_cache.json",
            fallback_data=FALLBACK_QUOTES,
            content_type="quote",
            cache_hours=Config.display.quote_cache_hours,
        )

    async def get_quote(self, client: httpx.AsyncClient | None = None) -> Quote:
        """Get current quote (cached or fresh).

        Args:
            client: Optional Async HTTP client

        Returns:
            Quote dictionary with content, author, and source
        """
        return await self.get_content(client)

    async def _fetch_content(self, client: httpx.AsyncClient | None = None) -> Quote:
        """Fetch English quote from Quotable API.

        Args:
            client: Optional Async HTTP client

        Returns:
            Quote dictionary

        Raises:
            httpx.HTTPError: If HTTP request fails
        """
        url = "http://api.quotable.io/random"

        if client:
            response = await client.get(url, timeout=5.0)
        else:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(5.0, connect=5.0),
                limits=httpx.Limits(max_connections=2, max_keepalive_connections=0),
            ) as new_client:
                response = await new_client.get(url)

        response.raise_for_status()
        data = response.json()

        return {
            "content": data["content"],
            "author": data["author"],
            "source": "",
        }


# Singleton instance
_quote_provider = None


async def get_quote(client: httpx.AsyncClient | None = None) -> Quote:
    """Get current quote (module-level function).

    Args:
        client: Optional Async HTTP client

    Returns:
        Quote dictionary
    """
    global _quote_provider
    if _quote_provider is None:
        _quote_provider = QuoteProvider()
    return await _quote_provider.get_quote(client)
