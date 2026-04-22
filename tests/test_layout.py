"""Tests for dashboard layout and image generation."""

from PIL import Image

from src.config import Config
from src.layouts import DashboardLayout


def test_layout_creation(monkeypatch):
    """Test basic layout creation with TODO lists."""
    # Mock Config to ensure consistent data - patch the grouped config
    monkeypatch.setattr(Config.api, "city_name", "TestCity")
    # Disable grayscale for consistent test results
    monkeypatch.setattr(Config.hardware, "use_grayscale", False)

    layout = DashboardLayout()

    # Mock data with all required fields
    data = {
        "weather": {"temp": "20.0", "desc": "Sunny", "icon": "Clear"},
        "github_commits": {"day": 5, "week": 23, "month": 90, "year": 860},
        "vps_usage": 50,
        "btc_price": {"usd": 50000, "usd_24h_change": 5.0},
        "week_progress": 75,
        "show_hackernews": False,  # Show TODO lists
        "todo_goals": ["Goal 1", "Goal 2"],
        "todo_must": ["Must 1", "Must 2"],
        "todo_optional": ["Optional 1"],
        "hackernews": {"stories": [], "page": 1, "total_pages": 1},
    }

    # Generate image
    img = layout.create_image(800, 480, data)

    assert isinstance(img, Image.Image)
    assert img.size == (800, 480)
    assert img.mode == "1"  # Black/white mode when grayscale is disabled


def test_layout_creation_grayscale(monkeypatch):
    """Test layout creation with grayscale mode enabled."""
    # Mock Config to ensure consistent data
    monkeypatch.setattr(Config.api, "city_name", "TestCity")
    # Enable grayscale mode
    monkeypatch.setattr(Config.hardware, "use_grayscale", True)

    layout = DashboardLayout()

    # Mock data
    data = {
        "weather": {"temp": "20.0", "desc": "Sunny", "icon": "Clear"},
        "github_commits": {"day": 5, "week": 23, "month": 90, "year": 860},
        "vps_usage": 50,
        "btc_price": {"usd": 50000, "usd_24h_change": 5.0},
        "week_progress": 75,
        "show_hackernews": False,
        "todo_goals": ["Goal 1"],
        "todo_must": ["Must 1"],
        "todo_optional": ["Optional 1"],
        "hackernews": {"stories": [], "page": 1, "total_pages": 1},
    }

    # Generate image
    img = layout.create_image(800, 480, data)

    assert isinstance(img, Image.Image)
    assert img.size == (800, 480)
    assert img.mode == "L"  # Grayscale mode when enabled


def test_layout_hackernews_mode(monkeypatch):
    """Test layout with HackerNews display mode."""
    monkeypatch.setattr(Config.api, "city_name", "TestCity")
    monkeypatch.setattr(Config.hardware, "use_grayscale", False)

    layout = DashboardLayout()

    # Mock data with HackerNews
    data = {
        "weather": {"temp": "20.0", "desc": "Sunny", "icon": "Clear"},
        "github_commits": {"day": 5, "week": 23, "month": 90, "year": 860},
        "vps_usage": 50,
        "btc_price": {"usd": 50000, "usd_24h_change": 5.0},
        "week_progress": 75,
        "show_hackernews": True,  # Show HackerNews
        "hackernews": {
            "stories": [
                {"title": "Test Story 1", "score": 100},
                {"title": "Test Story 2", "score": 200},
            ],
            "page": 1,
            "total_pages": 10,
            "start_idx": 1,
            "end_idx": 5,
        },
    }

    # Generate image
    img = layout.create_image(800, 480, data)

    assert isinstance(img, Image.Image)
    assert img.size == (800, 480)
    assert img.mode == "1"


def test_layout_with_claude_usage_rings(monkeypatch):
    """Test layout renders with Claude usage dual-ring footer item."""
    monkeypatch.setattr(Config.api, "city_name", "TestCity")
    monkeypatch.setattr(Config.hardware, "use_grayscale", False)

    layout = DashboardLayout()

    data = {
        "weather": {"temp": "20.0", "desc": "Sunny", "icon": "Clear"},
        "github_commits": {"day": 5, "week": 23, "month": 90, "year": 860},
        "vps_usage": 50,
        "btc_price": {"usd": 50000, "usd_24h_change": 5.0},
        "week_progress": 75,
        "claude_usage": {"five_hour": 42, "weekly": 66},
        "show_hackernews": False,
        "todo_goals": ["Goal 1"],
        "todo_must": ["Must 1"],
        "todo_optional": ["Optional 1"],
        "hackernews": {"stories": [], "page": 1, "total_pages": 1},
    }

    img = layout.create_image(800, 480, data)

    assert isinstance(img, Image.Image)
    assert img.size == (800, 480)
    assert img.mode == "1"
