"""Weather data provider using OpenWeatherMap API.

Fetches current weather data with caching and retry logic.
"""

import logging

import httpx

from src.config import Config
from src.core import api_retry, cached
from src.exceptions import ProviderError

logger = logging.getLogger(__name__)

OPENWEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"


@cached(ttl=600)  # Cache for 10 minutes
@api_retry
async def get_weather(client: httpx.AsyncClient) -> dict[str, str]:
    """Fetch current weather data from OpenWeatherMap API.

    Args:
        client: Async HTTP client instance

    Returns:
        Dictionary containing temperature, description, and icon name

    Raises:
        ProviderError: If API request fails
    """
    if not Config.api.openweather_api_key:
        logger.warning("OpenWeather API key not configured, using fallback")
        return {"temp": "13.9", "desc": "Sunny", "icon": "Clear"}

    url = OPENWEATHER_URL
    params = {"q": Config.api.city_name, "appid": Config.api.openweather_api_key, "units": "metric"}

    try:
        res = await client.get(url, params=params, timeout=10.0)
        res.raise_for_status()
        data = res.json()

        return {
            "temp": str(round(data["main"]["temp"], 1)),
            "desc": data["weather"][0]["main"],
            "icon": data["weather"][0]["main"],
        }
    except httpx.HTTPError as e:
        logger.error(f"Weather API Error: {e}")
        raise ProviderError("weather", "Failed to fetch weather data", e) from e
    except Exception as e:
        logger.error(f"Weather API Error: {e}")
        raise ProviderError("weather", "Unexpected error", e) from e
