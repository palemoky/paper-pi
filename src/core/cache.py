"""Caching utilities with TTL support for the E-Ink dashboard application.

This module provides decorators and utilities for caching function results
with time-to-live (TTL) expiration and LRU eviction policies.
"""

import asyncio
import functools
import logging
import time
from collections import OrderedDict
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

# Type variable for generic function
F = TypeVar("F", bound=Callable[..., Any])


class TTLCache:
    """Time-to-live cache with LRU eviction.

    Features:
    - TTL-based expiration
    - LRU eviction when max size reached
    - Thread-safe operations
    - Async-compatible

    Example:
        >>> cache = TTLCache(maxsize=100, ttl=300)
        >>> cache.set("key", "value")
        >>> value = cache.get("key")
    """

    def __init__(self, maxsize: int = 128, ttl: int = 300):
        """Initialize TTL cache.

        Args:
            maxsize: Maximum number of items to cache
            ttl: Time-to-live in seconds
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: Any) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # Check if expired
            if time.time() - timestamp > self.ttl:
                logger.debug(f"Cache expired: {key}")
                del self._cache[key]
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            logger.debug(f"Cache hit: {key}")
            return value

    async def set(self, key: Any, value: Any) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        async with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.maxsize and key not in self._cache:
                oldest_key = next(iter(self._cache))
                logger.debug(f"Cache eviction (LRU): {oldest_key}")
                del self._cache[oldest_key]

            # Add/update with current timestamp
            self._cache[key] = (value, time.time())
            self._cache.move_to_end(key)
            logger.debug(f"Cache set: {key}")

    async def delete(self, key: Any) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted: {key}")

    async def clear(self) -> None:
        """Clear all cached values."""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")

    def get_sync(self, key: Any) -> Any | None:
        """Synchronous get (no lock, use with caution)."""
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]
        if time.time() - timestamp > self.ttl:
            return None

        return value


def cached(ttl: int = 300, maxsize: int = 128, exclude_types: tuple | None = None):
    """Decorator for caching async function results with TTL.

    Args:
        ttl: Time-to-live in seconds
        maxsize: Maximum cache size
        exclude_types: Tuple of types to exclude from cache key generation.
                      Defaults to (httpx.AsyncClient, httpx.Client) to prevent
                      cache misses when different client instances are used.

    Example:
        >>> @cached(ttl=600)
        >>> async def fetch_data(client, param):
        >>>     # client will be excluded from cache key by default
        >>>     return await expensive_operation(client, param)
    """
    # Default: exclude HTTP clients from cache key to prevent cache misses
    # when different client instances are passed
    if exclude_types is None:
        try:
            import httpx

            exclude_types = (httpx.AsyncClient, httpx.Client)
        except ImportError:
            exclude_types = ()

    cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Filter args to exclude certain types from cache key
            filtered_args = tuple(arg for arg in args if not isinstance(arg, exclude_types))

            # Create cache key from filtered args and kwargs
            key = (filtered_args, tuple(sorted(kwargs.items())))

            # Check cache
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result)
            return result

        # Attach cache for manual control
        wrapper.cache = cache  # type: ignore
        return wrapper  # type: ignore

    return decorator


def cache_key(*args, **kwargs) -> tuple:
    """Generate cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Hashable cache key tuple
    """
    return (args, tuple(sorted(kwargs.items())))
