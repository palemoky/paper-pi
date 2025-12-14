"""Type definitions for the E-Ink dashboard application.

This module contains TypedDict definitions and type aliases for improved type safety
and better IDE support throughout the application.
"""

from typing import TypedDict


class WeatherData(TypedDict):
    """Weather information from OpenWeatherMap API."""

    temp: str  # Temperature in Celsius
    desc: str  # Weather description (e.g., "Sunny", "Cloudy")
    icon: str  # Weather icon name/main status


class GitHubCommits(TypedDict):
    """GitHub contribution statistics."""

    day: int  # Commits today
    week: int  # Commits this week
    month: int  # Commits this month
    year: int  # Commits this year


class BTCData(TypedDict):
    """Bitcoin price information from CoinGecko API."""

    usd: int | str  # Current USD price (can be "---" on error)
    usd_24h_change: float  # 24-hour price change percentage


class HackerNewsStory(TypedDict):
    """Individual Hacker News story."""

    id: int  # Story ID
    title: str  # Story title
    score: int  # Story score (upvotes)
    url: str  # Story URL (either external URL or HN item URL)


class HackerNewsData(TypedDict):
    """Paginated Hacker News data."""

    stories: list[HackerNewsStory]  # Stories for current page
    page: int  # Current page number (1-indexed)
    total_pages: int  # Total number of pages
    start_idx: int  # Starting index (1-indexed)
    end_idx: int  # Ending index (1-indexed)


class GitHubYearSummary(TypedDict):
    """GitHub year-end contribution summary."""

    total: int  # Total contributions for the year
    max: int  # Maximum contributions in a single day
    avg: float  # Average daily contributions


class HolidayData(TypedDict):
    """Holiday greeting information."""

    name: str  # Holiday name
    title: str  # Display title
    message: str  # Greeting message
    icon: str  # Icon name


class QuoteData(TypedDict):
    """Quote information."""

    text: str  # Quote text
    author: str  # Quote author


class PoetryData(TypedDict):
    """Poetry information."""

    title: str  # Poem title
    author: str  # Poet name
    content: list[str]  # Poem lines
    dynasty: str  # Dynasty/period


class DashboardData(TypedDict, total=False):
    """Complete dashboard data structure.

    Note: total=False allows partial dictionaries during construction.
    """

    weather: WeatherData
    github_commits: GitHubCommits
    vps_usage: int  # VPS data usage percentage (0-100)
    btc_price: BTCData
    week_progress: int  # Week progress percentage (0-100)
    todo_goals: list[str]
    todo_must: list[str]
    todo_optional: list[str]
    hackernews: HackerNewsData
    show_hackernews: bool  # Whether to show HN instead of TODO
    github_year_summary: GitHubYearSummary | None
    quote: QuoteData | None
    poetry: PoetryData | None
    holiday: HolidayData | None
