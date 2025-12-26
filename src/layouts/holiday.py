"""Holiday detection and greeting management.

Detects special dates (birthdays, anniversaries, traditional holidays)
and provides appropriate greeting messages and icons.
"""

import pendulum
from borax.calendars.lunardate import LunarDate

from ..config import Config


class HolidayManager:
    """Manages holiday detection and greeting generation.

    Supports both solar calendar (birthdays, anniversaries) and
    lunar calendar (Chinese traditional festivals) holidays.
    """

    def __init__(self):
        pass

    def get_holiday(self) -> dict[str, str] | None:
        """
        检查今天是否是特殊节日
        Returns:
            dict or None: 如果是节日，返回 {'name': 'Birthday', 'icon': 'cake', 'message': 'Happy Birthday!'}
                          否则返回 None
        """
        now = pendulum.now(Config.hardware.timezone)
        today_str = now.format("MM-DD")
        lunar = LunarDate.from_solar_date(now.year, now.month, now.day)

        # 收集所有匹配的节日
        matched_holidays = []

        # 1. 检查公历节日
        if Config.personal.birthday and today_str == Config.personal.birthday:
            matched_holidays.append("birthday")

        if Config.personal.anniversary and today_str == Config.personal.anniversary:
            matched_holidays.append("anniversary")

        # 2. 特殊情况：生日和纪念日在同一天
        if "birthday" in matched_holidays and "anniversary" in matched_holidays:
            return {
                "name": "Birthday & Anniversary",
                "title": "Double Celebration!",
                "message": f"Happy Birthday & Anniversary, {Config.personal.user_name}!",
                "icon": "heart",
            }

        # 3. 单独的生日或纪念日
        holiday_data = {
            "birthday": {
                "name": "Birthday",
                "title": "Happy Birthday!",
                "message": f"To {Config.personal.user_name}",
                "icon": "birthday",
            },
            "anniversary": {
                "name": "Anniversary",
                "title": "Happy Anniversary!",
                "message": "Love & Peace",
                "icon": "heart",
            },
        }

        for holiday_key, data in holiday_data.items():
            if holiday_key in matched_holidays:
                return data

        # 4. 其他公历节日
        solar_holidays = {
            "01-01": {
                "name": "New Year",
                "title": f"Hello {now.year}!",
                "message": "New Beginnings",
                "icon": "firework",
            },
            "02-14": {
                "name": "Valentine's Day",
                "title": "Happy Valentine's Day!",
                "message": "Love & Romance",
                "icon": "love",
            },
            "12-31": {
                "name": "New Year's Eve",
                "title": f"Goodbye {now.year}!",
                "message": "Year-End Celebration",
                "icon": "celebration",
            },
            "12-25": {
                "name": "Christmas",
                "title": "Merry Christmas!",
                "message": "Jingle Bells",
                "icon": "tree",
            },
        }

        if today_str in solar_holidays:
            return solar_holidays[today_str]

        # 5. 匹配农历日期
        lunar_holidays = {
            (1, 1): {
                "name": "Spring Festival",
                "title": "Happy New Year!",
                "message": "Spring Festival",
                "icon": "lantern",
            },
            (8, 15): {
                "name": "Mid-Autumn",
                "title": "Mid-Autumn Festival",
                "message": "Mooncake & Family",
                "icon": "mooncake",
            },
        }

        lunar_key = (lunar.month, lunar.day)
        if lunar_key in lunar_holidays:
            return lunar_holidays[lunar_key]

        # 6. 特殊逻辑：除夕 (需要计算明天是否是正月初一)
        tomorrow = now.add(days=1)
        tomorrow_lunar = LunarDate.from_solar_date(tomorrow.year, tomorrow.month, tomorrow.day)
        if tomorrow_lunar.month == 1 and tomorrow_lunar.day == 1:
            return {
                "name": "New Year's Eve",
                "title": "Happy New Year's Eve",
                "message": "Reunion Dinner",
                "icon": "firecracker",
            }

        return None
