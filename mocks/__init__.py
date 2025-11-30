"""Mock package for development and debugging."""

from .data import (
    get_mock_cipaiming_poetry_data,
    get_mock_dashboard_data,
    get_mock_holiday_data,
    get_mock_qiyan_jueju_poetry_data,
    get_mock_qiyan_lvshi_poetry_data,
    get_mock_quote_data,
    get_mock_wuyan_jueju_poetry_data,
    get_mock_wuyan_longlvshi_poetry_data,
    get_mock_wuyan_lvshi_poetry_data,
    get_mock_xiaoling_poetry_data,
    get_mock_year_end_data,
)
from .driver import MockEPD

__all__ = [
    "MockEPD",
    "get_mock_dashboard_data",
    "get_mock_holiday_data",
    "get_mock_year_end_data",
    "get_mock_quote_data",
    "get_mock_wuyan_jueju_poetry_data",
    "get_mock_wuyan_lvshi_poetry_data",
    "get_mock_wuyan_longlvshi_poetry_data",
    "get_mock_qiyan_lvshi_poetry_data",
    "get_mock_cipaiming_poetry_data",
    "get_mock_qiyan_jueju_poetry_data",
    "get_mock_xiaoling_poetry_data",
]
