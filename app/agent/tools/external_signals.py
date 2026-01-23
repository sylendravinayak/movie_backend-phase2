import requests
from datetime import datetime, timedelta
from typing import Dict, List
import os
from functools import lru_cache
import numpy as np 

SERP_API_KEY = os.getenv("SERP_API_KEY","5ca9d28f15c1656bba9f2075886375108eb524821d1cd5ba320e37a0dc1c3cbe")
HOLIDAY_API_KEY = os.getenv("CALENDARIFIC_API_KEY","FeCmlH07BjBytqCE5cg0UYFOLzJa3oE8")


# ===========================
# Google Trends via SerpAPI
# ===========================
class TrendAnalyzer:

    @staticmethod
    @lru_cache(maxsize=100)
    def get_monthly_trend(movie_title: str, days: int = 30) -> List[Dict]:

        if not SERP_API_KEY:
            return TrendAnalyzer._mock_trend_data(days)

        try:
            url = "https://serpapi.com/search.json"

            params = {
                "engine": "google_trends",
                "q[]": movie_title,
                "date": "today 1-m",
                "geo": "IN-TN",
                "api_key": SERP_API_KEY
            }

            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            timeline = data.get("interest_over_time", {}).get("timeline_data", [])
            print(f"✅ Retrieved trend data for '{movie_title}' with {timeline} points")
            trend_series = []

            for p in timeline:
                try:
                    if "timestamp" in p:
                        dt = datetime.fromtimestamp(int(p["timestamp"]))
                  
                    elif "date" in p:
                        dt = datetime.strptime(p["date"], "%b %d, %Y")

                    else:
                        continue  

                    value = (
                        p.get("values", [{}])[0].get("extracted_value", 0)
                    )

                    trend_series.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "value": int(value)
                    })

                except Exception as e:
                    continue


            return trend_series if trend_series else TrendAnalyzer._mock_trend_data(days)

        except Exception as e:
            print(f"❌ SerpAPI error: {e}")
            return TrendAnalyzer._mock_trend_data(days)

    @staticmethod
    def _mock_trend_data(days: int) -> List[Dict]:
        base = 50
        out = []
        for i in range(days):
            dt = datetime.now() - timedelta(days=days-i)
            value = base + i * 0.4 + (i % 7) * 3
            value = min(100, max(0, int(value)))
            out.append({
                "date": dt.strftime("%Y-%m-%d"),
                "value": value
            })
        return out

    @staticmethod
    def calculate_trend_momentum(trend_data: List[Dict]) -> float:
        if not trend_data or len(trend_data) < 7:
            return 1.0

        recent = sum(d["value"] for d in trend_data[-7:]) / 7
        past = sum(d["value"] for d in trend_data[:-7]) / max(len(trend_data)-7,1)

        if past == 0:
            return 1.0

        return max(0.5, min(recent / past, 1.5))


# ===========================
# Holiday Calendar
# ===========================
class HolidayCalendar:

    @staticmethod
    @lru_cache(maxsize=1)
    def get_holidays(year: int) -> List[Dict]:

        if not HOLIDAY_API_KEY:
            return HolidayCalendar._mock_holidays(year)

        try:
            url = "https://calendarific.com/api/v2/holidays"

            params = {
                "api_key": HOLIDAY_API_KEY,
                "country": "IN",
                "year": year,
                "location": "IN-TN"
            }

            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            holidays = []
            for h in data.get("response", {}).get("holidays", []):
                iso = h.get("date", {}).get("iso")
                if iso:
                    holidays.append({
                        "date": iso.split("T")[0],
                        "name": h.get("name", ""),
                        "type": h.get("type", ["Holiday"])[0]
                    })

            return holidays

        except Exception as e:
            print(f"❌ Holiday API error: {e}")
            return HolidayCalendar._mock_holidays(year)

    @staticmethod
    def _mock_holidays(year: int) -> List[Dict]:
        return [
            {"date": f"{year}-01-14", "name": "Pongal", "type": "Regional"},
            {"date": f"{year}-01-26", "name": "Republic Day", "type": "National"},
            {"date": f"{year}-04-14", "name": "Tamil New Year", "type": "Regional"},
            {"date": f"{year}-08-15", "name": "Independence Day", "type": "National"},
            {"date": f"{year}-10-02", "name": "Gandhi Jayanti", "type": "National"},
            {"date": f"{year}-12-25", "name": "Christmas", "type": "National"},
        ]

    @staticmethod
    def is_holiday(date_str: str, holidays: List[Dict]) -> Dict:
        return next((h for h in holidays if h["date"] == date_str), None)

    @staticmethod
    def get_holiday_boost(date_str: str, holidays: List[Dict]) -> float:
        h = HolidayCalendar.is_holiday(date_str, holidays)
        if not h:
            return 1.0

        if h["type"] == "National":
            return 1.35
        elif h["type"] == "Regional":
            return 1.25
        return 1.15


# ===========================
# Unified External Signals
# ===========================
def fetch_all_external_signals(movie_titles: List[str]) -> Dict:

    trends = {}

    for t in movie_titles:
        print(f"📊 Fetching trend data for: {t}")
        trends[t] = TrendAnalyzer.get_monthly_trend(t, 30)

    year = datetime.now().year
    holidays = HolidayCalendar.get_holidays(year)

    if datetime.now().month == 12:
        holidays.extend(HolidayCalendar.get_holidays(year+1))

    return {
        "trends": trends,
        "holidays": holidays
    }

def get_trend_factor(movie_title: str, trend_data: Dict) -> float:
    """
    Converts SerpAPI trend series into a demand multiplier
    Returns: 0.8 – 1.4
    """
    series = trend_data.get(movie_title, [])
    if not series or len(series) < 7:
        return 1.0

    recent = np.mean([d["value"] for d in series[-7:]])
    base = np.mean([d["value"] for d in series[:-7]]) if len(series) > 7 else recent

    if base == 0:
        return 1.0

    factor = recent / base
    return float(np.clip(factor, 0.8, 1.4))
