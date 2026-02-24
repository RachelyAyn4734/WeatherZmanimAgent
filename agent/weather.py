"""Open-Meteo API client for weather forecasts."""
import aiohttp
import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather code descriptions (Hebrew)
WMO_CODES_HE = {
    0: "שמיים בהירים", 1: "בהיר בעיקר", 2: "מעונן חלקית", 3: "מעונן",
    45: "ערפל", 48: "ערפל קפוא",
    51: "טפטוף קל", 53: "טפטוף בינוני", 55: "טפטוף כבד",
    61: "גשם קל", 63: "גשם בינוני", 65: "גשם כבד",
    71: "שלג קל", 73: "שלג בינוני", 75: "שלג כבד",
    80: "מטר קל", 81: "מטר בינוני", 82: "מטר כבד",
    95: "סופת ברקים", 96: "סופת ברקים עם ברד",
}

WMO_EMOJI = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️",
}


class WeatherClient:
    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon

    async def get_full_forecast(self) -> Dict[str, Any]:
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "hourly": ",".join([
                "temperature_2m",
                "apparent_temperature",
                "wind_speed_10m",
                "wind_direction_10m",
                "visibility",
                "precipitation_probability",
                "precipitation",
                "weather_code",
                "relative_humidity_2m",
            ]),
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "weather_code",
                "sunrise",
                "sunset",
            ]),
            "forecast_days": 10,
            "timezone": "Asia/Jerusalem",
            "wind_speed_unit": "kmh",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(OPEN_METEO_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json()

        log.info(
            "Weather data fetched. Today max: %s°C, min: %s°C",
            data.get("daily", {}).get("temperature_2m_max", [None])[0],
            data.get("daily", {}).get("temperature_2m_min", [None])[0],
        )
        return data

    @staticmethod
    def code_to_description(code: int) -> str:
        return WMO_CODES_HE.get(code, "לא ידוע")

    @staticmethod
    def code_to_emoji(code: int) -> str:
        return WMO_EMOJI.get(code, "🌡️")
