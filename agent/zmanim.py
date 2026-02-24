"""Hebcal API client for Jewish times (zmanim), Shabbat and parasha."""
import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import date

log = logging.getLogger(__name__)

HEBCAL_ZMANIM_URL = "https://www.hebcal.com/zmanim"
HEBCAL_SHABBAT_URL = "https://www.hebcal.com/shabbat"
HEBCAL_HEBCAL_URL = "https://www.hebcal.com/hebcal"

# Hebrew labels for zmanim keys returned by Hebcal
ZMANIM_LABELS_HE = {
    "alotHaShachar": "עלות השחר",
    "misheyakir": "משיכיר",
    "dawn": "שחר",
    "sunrise": "זריחה",
    "sofZmanShma": "סוף זמן ק\"ש (גר\"א)",
    "sofZmanTfilla": "סוף זמן תפילה",
    "chatzot": "חצות",
    "minchaGedola": "מנחה גדולה",
    "minchaKetana": "מנחה קטנה",
    "plagHaMincha": "פלג המנחה",
    "sunset": "שקיעה",
    "beinHaShmashos": "בין השמשות",
    "tzeit7083deg": "צאת הכוכבים",
    "tzeit85deg": "צאת הכוכבים (מחמיר)",
    "chatzotLayla": "חצות הלילה",
}


class ZmanimClient:
    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon

    async def get_zmanim(self, target_date: date) -> Dict[str, Any]:
        """Fetch full zmanim for a given date."""
        params = {
            "cfg": "json",
            "latitude": self.lat,
            "longitude": self.lon,
            "tzid": "Asia/Jerusalem",
            "date": target_date.strftime("%Y-%m-%d"),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                HEBCAL_ZMANIM_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        log.info("Zmanim fetched for %s", target_date)
        return data

    async def get_shabbat_times(self, friday_date: date) -> Optional[Dict[str, Any]]:
        """Fetch candle lighting and Havdalah times for the coming Shabbat."""
        params = {
            "cfg": "json",
            "latitude": self.lat,
            "longitude": self.lon,
            "tzid": "Asia/Jerusalem",
            "M": "on",
            "lg": "he",
            "b": 18,  # candle lighting minutes before sunset
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    HEBCAL_SHABBAT_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            log.info("Shabbat times fetched for week of %s", friday_date)
            return data
        except Exception as e:
            log.warning("Failed to fetch Shabbat times: %s", e)
            return None

    async def get_weekly_parasha(self, target_date: date) -> Optional[str]:
        """Return the Hebrew name of the weekly Torah portion."""
        params = {
            "v": 1,
            "cfg": "json",
            "s": "on",
            "start": target_date.strftime("%Y-%m-%d"),
            "end": target_date.strftime("%Y-%m-%d"),
            "tzid": "Asia/Jerusalem",
            "lg": "he",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    HEBCAL_HEBCAL_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            for item in data.get("items", []):
                if item.get("category") == "parashat":
                    return item.get("hebrew") or item.get("title")
        except Exception as e:
            log.warning("Failed to fetch parasha: %s", e)

        return None

    @staticmethod
    def extract_time(zmanim_data: Dict[str, Any], key: str) -> Optional[str]:
        """Extract HH:MM from a zmanim dict entry."""
        times = zmanim_data.get("times", {})
        value = times.get(key)
        if value:
            # Hebcal returns ISO format like "2026-02-18T06:15:00+02:00"
            try:
                return value[11:16]  # "HH:MM"
            except Exception:
                return value
        return None

    @staticmethod
    def get_label(key: str) -> str:
        return ZMANIM_LABELS_HE.get(key, key)
