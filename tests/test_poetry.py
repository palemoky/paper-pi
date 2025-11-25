"""Test script for poetry provider functionality."""

import logging

import pytest

from src.providers.poetry import get_poetry

logging.basicConfig(level=logging.INFO)


@pytest.mark.asyncio
async def test_poetry_fetching():
    """Test poetry fetching from all sources."""
    print("\n" + "=" * 60)
    print("Testing Poetry Provider")
    print("=" * 60 + "\n")

    # Test 1: Get a poetry
    print("Test 1: Fetching poetry...")
    poetry = await get_poetry()
    print("✅ Poetry fetched successfully!")
    print(f"   Type: {poetry['type']}")
    print(f"   Content: {poetry['content'][:50]}...")
    print(f"   Author: {poetry['author']}")
    print(f"   Source: {poetry['source']}")

    # Test 2: Check caching
    print("\nTest 2: Testing cache...")
    poetry2 = await get_poetry()
    if poetry == poetry2:
        print("✅ Cache working! Same poetry returned.")
    else:
        print("⚠️  Different poetry returned (cache may have expired)")

    # Test 3: Display formatted poetry
    print("\n" + "=" * 60)
    print("Formatted Poetry Display:")
    print("=" * 60)
    print(f"\n{poetry['content']}\n")
    attribution = f"—— {poetry['author']}"
    if poetry["source"]:
        attribution += f"《{poetry['source']}》"
    print(attribution)
    print("\n" + "=" * 60)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_poetry_fetching())
