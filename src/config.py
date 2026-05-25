"""Application configuration settings with grouped models and hot reload support.

Loads configuration from environment variables and .env file using python-dotenv.
All settings can be overridden via environment variables using flat naming (e.g., DISPLAY_MODE).

Configuration is organized into logical groups for better maintainability.
"""

import logging
import os
from pathlib import Path
from typing import Literal

import httpx
import pendulum
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

DEFAULT_POETRY_API_URL = "https://poetry.palemoky.com/api/poems/random"

# ===== HTTP Client Defaults =====
# Shared by all providers to ensure consistent connection management.
# max_connections: limits concurrent sockets (prevents fd exhaustion under load)
# max_keepalive_connections=0: close idle sockets eagerly (prevents fd accumulation
# when network is unreachable and requests fail repeatedly)
HTTP_LIMITS = httpx.Limits(max_connections=5, max_keepalive_connections=0)
HTTP_TIMEOUT = httpx.Timeout(timeout=15.0, connect=10.0)


def _seconds_until_midnight(timezone: str = "Asia/Shanghai") -> int:
    """Calculate seconds until next midnight (0:01) in the given timezone.

    Args:
        timezone: IANA timezone name (e.g., "Asia/Shanghai")

    Returns:
        Number of seconds until midnight
    """
    now = pendulum.now(timezone)
    # Get tomorrow at 00:00:00
    midnight = now.add(days=1).start_of("day")
    # Calculate seconds difference
    return int((midnight - now).total_seconds()) + 60


# ===== Configuration Groups =====


class DisplayConfig(BaseModel):
    """Display mode and related settings."""

    mode: Literal["dashboard", "poetry", "quote", "wallpaper"] = Field(
        default="dashboard",
        description="Display mode: dashboard, poetry, quote, or wallpaper",
    )
    wallpaper_name: str = Field(default="", description="Wallpaper name (empty for random)")
    quote_cache_hours: int = Field(default=1, description="Quote cache duration in hours", ge=1)

    # Refresh intervals for different modes (in seconds)
    refresh_interval_dashboard: int = Field(
        default=600, description="Dashboard mode refresh interval in seconds", ge=60
    )
    refresh_interval_quote: int = Field(
        default=3600, description="Quote mode refresh interval in seconds", ge=60
    )
    refresh_interval_poetry: int = Field(
        default=3600, description="Poetry mode refresh interval in seconds", ge=60
    )
    refresh_interval_wallpaper: int = Field(
        default=0,
        description="Wallpaper mode refresh interval in seconds (0 = no refresh for static wallpaper)",
        ge=0,
    )
    refresh_interval_holiday: int = Field(
        default=86400,
        description="Holiday mode refresh interval in seconds (default: until midnight)",
        ge=60,
    )
    refresh_interval_year_end: int = Field(
        default=86400,
        description="Year-end summary mode refresh interval in seconds (default: until midnight)",
        ge=60,
    )
    # HackerNews pagination settings
    hackernews_refresh_minutes: int = Field(
        default=60, description="HackerNews cache refresh interval in minutes", ge=1
    )
    hackernews_page_seconds: int = Field(
        default=30, description="HackerNews page display duration in seconds", ge=5
    )
    hackernews_stories_per_page: int = Field(
        default=5, description="Number of stories per page", ge=1, le=50
    )
    # HackerNews Gist integration (optional)
    hackernews_gist_id: str = Field(
        default="", description="GitHub Gist ID for saving HackerNews stories (optional)"
    )
    # Time slots for TODO display (format: "0-12,18-24" means show during these hours)
    # HackerNews will automatically show during non-TODO hours
    todo_time_slots: str = Field(
        default="0-12,18-24", description="Time slots for TODO display (hour ranges)"
    )
    # Poetry API configuration (uses hosted API by default)
    poetry_api_url: str = Field(
        default=DEFAULT_POETRY_API_URL,
        description="Poetry API URL (defaults to hosted public endpoint)",
    )

    @classmethod
    def from_env(cls) -> "DisplayConfig":
        """Load configuration from environment variables."""
        # Get timezone for calculating seconds until midnight
        timezone = os.getenv("TIMEZONE", "Asia/Shanghai")

        return cls(
            mode=os.getenv("DISPLAY_MODE", "dashboard"),
            wallpaper_name=os.getenv("WALLPAPER_NAME", ""),
            quote_cache_hours=int(os.getenv("QUOTE_CACHE_HOURS", "1")),
            refresh_interval_dashboard=int(os.getenv("REFRESH_INTERVAL_DASHBOARD", "600")),
            refresh_interval_quote=int(os.getenv("REFRESH_INTERVAL_QUOTE", "3600")),
            refresh_interval_poetry=int(os.getenv("REFRESH_INTERVAL_POETRY", "3600")),
            refresh_interval_wallpaper=int(os.getenv("REFRESH_INTERVAL_WALLPAPER", "0")),
            # Calculate seconds until midnight for holiday and year-end modes
            refresh_interval_holiday=int(
                os.getenv("REFRESH_INTERVAL_HOLIDAY", str(_seconds_until_midnight(timezone)))
            ),
            refresh_interval_year_end=int(
                os.getenv("REFRESH_INTERVAL_YEAR_END", str(_seconds_until_midnight(timezone)))
            ),
            hackernews_refresh_minutes=int(os.getenv("HACKERNEWS_REFRESH_MINUTES", "60")),
            hackernews_page_seconds=int(os.getenv("HACKERNEWS_PAGE_SECONDS", "30")),
            hackernews_stories_per_page=int(os.getenv("HACKERNEWS_STORIES_PER_PAGE", "5")),
            hackernews_gist_id=os.getenv("HACKERNEWS_GIST_ID", ""),
            todo_time_slots=os.getenv("TODO_TIME_SLOTS", "0-12,18-24"),
            poetry_api_url=os.getenv("POETRY_API_URL", DEFAULT_POETRY_API_URL),
        )


class HardwareConfig(BaseModel):
    """Hardware and E-Paper display settings."""

    refresh_interval: int = Field(default=600, description="Refresh interval in seconds", ge=60)
    is_screenshot_mode: bool = Field(
        default=False, description="Screenshot mode (saves to file instead of display)"
    )
    quiet_start_hour: int = Field(
        default=1, description="Quiet hours start (24h format)", ge=0, le=23
    )
    quiet_end_hour: int = Field(default=6, description="Quiet hours end (24h format)", ge=0, le=23)
    timezone: str = Field(default="Asia/Shanghai", description="IANA timezone name")
    epd_model: str = Field(default="epd7in5_V2", description="E-Paper driver model")
    mock_epd: bool = Field(default=False, description="Force using Mock driver for testing")
    use_grayscale: bool = Field(
        default=True, description="Enable 4-level grayscale mode for better visual hierarchy"
    )

    @classmethod
    def from_env(cls) -> "HardwareConfig":
        """Load configuration from environment variables."""
        return cls(
            refresh_interval=int(os.getenv("REFRESH_INTERVAL", "600")),
            is_screenshot_mode=os.getenv("IS_SCREENSHOT_MODE", "false").lower() == "true",
            quiet_start_hour=int(os.getenv("QUIET_START_HOUR", "1")),
            quiet_end_hour=int(os.getenv("QUIET_END_HOUR", "6")),
            timezone=os.getenv("TIMEZONE", "Asia/Shanghai"),
            epd_model=os.getenv("EPD_MODEL", "epd7in5_V2"),
            mock_epd=os.getenv("MOCK_EPD", "false").lower() == "true",
            use_grayscale=os.getenv("HARDWARE_USE_GRAYSCALE", "true").lower() == "true",
        )


class PersonalConfig(BaseModel):
    """Personal information for greetings and holidays."""

    user_name: str = Field(default="Palemoky", description="User name")
    birthday: str = Field(default="", description="Birthday in MM-DD format")
    anniversary: str = Field(default="", description="Anniversary in MM-DD format")
    greeting_label: str = Field(default="Palemoky", description="Greeting label")
    greeting_text: str = Field(default="Stay Focused", description="Greeting text")

    @field_validator("birthday", "anniversary")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate MM-DD format."""
        if v and (len(v) != 5 or v[2] != "-"):
            raise ValueError("Date must be in MM-DD format")
        return v

    @classmethod
    def from_env(cls) -> "PersonalConfig":
        """Load configuration from environment variables."""
        return cls(
            user_name=os.getenv("USER_NAME", "Palemoky"),
            birthday=os.getenv("BIRTHDAY", ""),
            anniversary=os.getenv("ANNIVERSARY", ""),
            greeting_label=os.getenv("GREETING_LABEL", "Palemoky"),
            greeting_text=os.getenv("GREETING_TEXT", "Stay Focused"),
        )


class APIConfig(BaseModel):
    """External API credentials and settings."""

    openweather_api_key: str = Field(default="", description="OpenWeatherMap API key")
    city_name: str = Field(default="Beijing", description="City name for weather")
    vps_api_key: str = Field(default="", description="VPS API key (64clouds)")
    claude_oauth_token: str = Field(default="", description="Claude Code OAuth token")
    claude_oauth_token_file: str = Field(
        default="", description="Claude OAuth token file path (preferred in Docker)"
    )
    chatgpt_oauth_token: str = Field(default="", description="ChatGPT/Codex OAuth token")
    chatgpt_oauth_token_file: str = Field(
        default="", description="ChatGPT OAuth token file path (preferred in Docker)"
    )
    chatgpt_account_id: str = Field(default="", description="Optional ChatGPT account ID")
    chatgpt_base_url: str = Field(
        default="https://chatgpt.com/backend-api",
        description="ChatGPT backend API base URL",
    )
    kimi_api_key: str = Field(default="", description="Kimi Code API key")
    kimi_api_key_file: str = Field(
        default="", description="Kimi API key file path (preferred in Docker)"
    )
    kimi_base_url: str = Field(
        default="https://api.kimi.com/coding/v1",
        description="Kimi Code API base URL",
    )

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Load configuration from environment variables."""
        return cls(
            openweather_api_key=os.getenv("OPENWEATHER_API_KEY", ""),
            city_name=os.getenv("CITY_NAME", "Beijing"),
            vps_api_key=os.getenv("VPS_API_KEY", ""),
            claude_oauth_token=os.getenv("CLAUDE_OAUTH_TOKEN", ""),
            claude_oauth_token_file=os.getenv("CLAUDE_OAUTH_TOKEN_FILE", ""),
            chatgpt_oauth_token=os.getenv("CHATGPT_OAUTH_TOKEN", ""),
            chatgpt_oauth_token_file=os.getenv("CHATGPT_OAUTH_TOKEN_FILE", ""),
            chatgpt_account_id=os.getenv("CHATGPT_ACCOUNT_ID", ""),
            chatgpt_base_url=os.getenv("CHATGPT_BASE_URL", "https://chatgpt.com/backend-api"),
            kimi_api_key=os.getenv("KIMI_API_KEY", ""),
            kimi_api_key_file=os.getenv("KIMI_API_KEY_FILE", ""),
            kimi_base_url=os.getenv(
                "KIMI_BASE_URL",
                os.getenv("KIMI_CODE_BASE_URL", "https://api.kimi.com/coding/v1"),
            ),
        )


class GitHubConfig(BaseModel):
    """GitHub integration settings."""

    username: str = Field(default="", description="GitHub username")
    token: str = Field(default="", description="GitHub personal access token")

    @classmethod
    def from_env(cls) -> "GitHubConfig":
        """Load configuration from environment variables."""
        return cls(
            username=os.getenv("GITHUB_USERNAME", ""),
            token=os.getenv("GITHUB_TOKEN", ""),
        )


class TODOConfig(BaseModel):
    """TODO list data source configuration."""

    source: Literal["config", "gist", "notion", "sheets"] = Field(
        default="config", description="TODO data source"
    )
    gist_id: str = Field(default="", description="GitHub Gist ID (if source=gist)")
    notion_token: str = Field(default="", description="Notion integration token (if source=notion)")
    notion_database_id: str = Field(default="", description="Notion database ID (if source=notion)")
    google_sheets_id: str = Field(default="", description="Google Sheets ID (if source=sheets)")
    google_credentials_file: str = Field(
        default="credentials.json", description="Google credentials file path"
    )
    # Default TODO lists
    list_goals: list[str] = Field(
        default_factory=lambda: [
            'Finish reading "Clean Code" by end of month',
            "Learn the basics of Rust programming",
            "Complete the Raspberry Pi e-ink dashboard project",
            "Improve spoken English to B2 level",
            "Run a 5km race in under 30 minutes",
            "Build a personal website portfolio",
            "Learn how to deploy apps with Docker and Kubernetes",
            "Write a blog post every week for 3 months",
            "Refactor legacy codebase at work",
            "Design and implement a home automation system",
        ],
        description="Default goals list",
    )
    list_must: list[str] = Field(
        default_factory=lambda: [
            'Finish reading "Clean Code" by end of month',
            "Learn the basics of Rust programming",
            "Complete the Raspberry Pi e-ink dashboard project",
            "Improve spoken English to B2 level",
            "Run a 5km race in under 30 minutes",
            "Build a personal website portfolio",
            "Learn how to deploy apps with Docker and Kubernetes",
            "Write a blog post every week for 3 months",
            "Refactor legacy codebase at work",
            "Design and implement a home automation system",
        ],
        description="Default must-do list",
    )
    list_optional: list[str] = Field(
        default_factory=lambda: [
            'Finish reading "Clean Code" by end of month',
            "Learn the basics of Rust programming",
            "Complete the Raspberry Pi e-ink dashboard project",
            "Improve spoken English to B2 level",
            "Run a 5km race in under 30 minutes",
            "Build a personal website portfolio",
            "Learn how to deploy apps with Docker and Kubernetes",
            "Write a blog post every week for 3 months",
            "Refactor legacy codebase at work",
            "Design and implement a home automation system",
        ],
        description="Default optional list",
    )

    @classmethod
    def from_env(cls) -> "TODOConfig":
        """Load configuration from environment variables."""
        # Note: list values are not loaded from env, use defaults or external sources
        return cls(
            source=os.getenv("TODO_SOURCE", "config"),
            gist_id=os.getenv("GIST_ID", ""),
            notion_token=os.getenv("NOTION_TOKEN", ""),
            notion_database_id=os.getenv("NOTION_DATABASE_ID", ""),
            google_sheets_id=os.getenv("GOOGLE_SHEETS_ID", ""),
            google_credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        )


# Default path constants
DEFAULT_FONT_PATH = str(BASE_DIR / "fonts/WaveShare.ttc")
DEFAULT_DATA_DIR = BASE_DIR / "data"


class PathConfig(BaseModel):
    """File paths and directories."""

    font_path: str = Field(default=DEFAULT_FONT_PATH, description="Font file path")
    data_dir: Path = Field(default=DEFAULT_DATA_DIR, description="Data directory")

    @classmethod
    def from_env(cls) -> "PathConfig":
        """Load configuration from environment variables."""
        return cls(
            font_path=os.getenv("FONT_PATH", DEFAULT_FONT_PATH),
            data_dir=Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR))),
        )


# ===== Main Settings Class =====


class Settings(BaseModel):
    """Main application settings with grouped configuration.

    All settings are loaded from environment variables using flat naming.
    Example: DISPLAY_MODE=dashboard, GITHUB_USERNAME=user
    """

    # Configuration groups
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    personal: PersonalConfig = Field(default_factory=PersonalConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    todo: TODOConfig = Field(default_factory=TODOConfig)
    paths: PathConfig = Field(default_factory=PathConfig)

    def __init__(self, **data):
        """Initialize settings by loading from .env file and environment variables."""
        # Load .env file (if exists) into environment
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=True)
            logger.debug(f"Loaded environment from {env_file}")

        # Load each config group from environment
        if not data:
            data = {
                "display": DisplayConfig.from_env(),
                "hardware": HardwareConfig.from_env(),
                "personal": PersonalConfig.from_env(),
                "api": APIConfig.from_env(),
                "github": GitHubConfig.from_env(),
                "todo": TODOConfig.from_env(),
                "paths": PathConfig.from_env(),
            }

        super().__init__(**data)

        # Ensure data directory exists
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)

    def validate_required(self):
        """Validate required environment variables and configuration consistency."""
        from src.exceptions import ConfigError

        # Common placeholder values that should be treated as missing
        placeholders = {"", "your_key_here", "your_token", "your_username", "your_api_key"}

        required = {
            "OPENWEATHER_API_KEY": ("OpenWeatherMap API key", self.api.openweather_api_key),
            "GITHUB_USERNAME": ("GitHub username", self.github.username),
            "GITHUB_TOKEN": ("GitHub personal access token", self.github.token),
        }

        missing = []
        for key, (desc, value) in required.items():
            if not value or value.lower() in placeholders:
                missing.append(f"  • {key}: {desc}")
                if "openweather" in key.lower():
                    missing.append("    Get from: https://openweathermap.org/api")
                elif "github" in key.lower() and "token" in key.lower():
                    missing.append("    Get from: https://github.com/settings/tokens")

        if missing:
            logger.error("❌ Missing required environment variables:")
            for item in missing:
                logger.error(item)
            logger.error("\nPlease set these variables in your .env file or environment.")
            raise ConfigError("Missing required configuration")

        # Cross-field validation
        validation_errors = []

        # Validate quiet hours
        if self.hardware.quiet_start_hour == self.hardware.quiet_end_hour:
            validation_errors.append(
                f"Quiet hours start and end cannot be the same ({self.hardware.quiet_start_hour})"
            )

        # Validate refresh intervals
        if self.display.hackernews_page_seconds >= self.display.hackernews_refresh_minutes * 60:
            validation_errors.append(
                f"HackerNews page duration ({self.display.hackernews_page_seconds}s) "
                f"should be less than refresh interval "
                f"({self.display.hackernews_refresh_minutes}min)"
            )

        # Validate TODO source dependencies
        if self.todo.source == "gist" and not self.todo.gist_id:
            validation_errors.append("TODO source is 'gist' but GIST_ID is not set")
        elif self.todo.source == "notion" and (
            not self.todo.notion_token or not self.todo.notion_database_id
        ):
            validation_errors.append(
                "TODO source is 'notion' but NOTION_TOKEN or NOTION_DATABASE_ID is not set"
            )
        elif self.todo.source == "sheets" and not self.todo.google_sheets_id:
            validation_errors.append("TODO source is 'sheets' but GOOGLE_SHEETS_ID is not set")

        if validation_errors:
            logger.error("❌ Configuration validation errors:")
            for error in validation_errors:
                logger.error(f"  • {error}")
            raise ConfigError("Invalid configuration")

        logger.info("✅ All required environment variables are set")
        logger.info("✅ Configuration validation passed")

    def reload(self):
        """Reload configuration from environment and .env file."""
        logger.info("🔄 Reloading configuration from .env file...")
        try:
            new_settings = Settings()

            # Update all groups
            self.display = new_settings.display
            self.hardware = new_settings.hardware
            self.personal = new_settings.personal
            self.api = new_settings.api
            self.github = new_settings.github
            self.todo = new_settings.todo
            self.paths = new_settings.paths

            logger.info("✅ Configuration reloaded successfully")
            logger.debug(f"   Display mode: {self.display.mode}")
            logger.debug(f"   Refresh interval: {self.hardware.refresh_interval}s")
            logger.debug(f"   Quote cache hours: {self.display.quote_cache_hours}h")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}", exc_info=True)
            raise


# ===== Global Configuration Instance =====

Config = Settings()
