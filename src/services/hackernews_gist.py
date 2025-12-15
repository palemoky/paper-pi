"""HackerNews Gist service for saving stories to GitHub Gist.

This module provides functionality to save HackerNews stories to a GitHub Gist
in Markdown format for easy access and reading.
"""

import logging

import httpx

from src.config import Config
from src.types import HackerNewsStory

logger = logging.getLogger(__name__)


def format_stories_markdown(stories: list[HackerNewsStory]) -> str:
    """Format HackerNews stories as a numbered Markdown list.

    Args:
        stories: List of HackerNews stories

    Returns:
        Markdown formatted string with numbered list

    Example output:
        1. [GPT 5.2](https://news.ycombinator.com/item?id=46252114) 1024▲
        2. [Show HN: My Project](https://example.com) 512▲
    """
    if not stories:
        return "# HackerNews Best Stories\n\nNo stories available.\n"

    lines = ["# HackerNews Best Stories\n"]
    lines.append(f"*Updated: {_get_current_time()}*\n")

    # Table header
    lines.append("| #  | Title | Score |")
    lines.append("|:--:|:------|:------|")

    for i, story in enumerate(stories, 1):
        title = story.get("title", "Untitled")
        score = story.get("score", 0)
        url = story.get("url", "")

        # If no URL, use HN item URL
        if not url:
            story_id = story.get("id", 0)
            url = f"https://news.ycombinator.com/item?id={story_id}"

        lines.append(f"| {i} | [{title}]({url}) | ▲{score} |")

    return "\n".join(lines)


def _get_current_time() -> str:
    """Get current time in readable format."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(Config.hardware.timezone)
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")


async def save_stories_to_gist(stories: list[HackerNewsStory], client: httpx.AsyncClient) -> bool:
    """Save HackerNews stories to GitHub Gist.

    Args:
        stories: List of HackerNews stories to save
        client: HTTP client for making requests

    Returns:
        True if successful, False otherwise
    """
    gist_id = Config.display.hackernews_gist_id
    github_token = Config.github.token

    # Skip if not configured
    if not gist_id or not github_token:
        logger.debug("HackerNews Gist not configured, skipping save")
        return False

    try:
        # Format stories as Markdown
        markdown_content = format_stories_markdown(stories)

        # Prepare Gist update payload
        url = f"https://api.github.com/gists/{gist_id}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {"files": {"hackernews.md": {"content": markdown_content}}}

        # Update Gist
        response = await client.patch(url, headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()

        logger.info(f"✅ Successfully saved {len(stories)} HN stories to Gist {gist_id}")
        return True

    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to update Gist (HTTP {e.response.status_code}): {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to save HN stories to Gist: {e}")
        return False
