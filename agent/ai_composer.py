"""Gemini AI composer for human-like email content."""
import os
import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)


class AIComposer:
    async def _ask_gemini(self, prompt: str, max_tokens: int = 400) -> str:
        """Send a prompt to Gemini and return the text response."""
        if not GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY not set — using fallback content.")
            return ""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.75,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    log.info("Gemini responded (%d chars)", len(text))
                    return text.strip()
        except Exception as e:
            log.warning("Gemini API error: %s — using fallback.", e)
            return ""

    # ------------------------------------------------------------------ #
    #  Morning report                                                      #
    # ------------------------------------------------------------------ #
    async def compose_morning_report(
        self,
        weather_data: Dict[str, Any],
        zmanim_data: Dict[str, Any],
        is_friday: bool,
        shabbat_data: Optional[Dict[str, Any]],
        parasha: Optional[str],
    ) -> Dict[str, str]:
        daily = weather_data.get("daily", {})
        max_t = daily.get("temperature_2m_max", [None])[0]
        min_t = daily.get("temperature_2m_min", [None])[0]
        wind = daily.get("wind_speed_10m_max", [None])[0]
        precip = daily.get("precipitation_sum", [None])[0]

        shabbat_line = ""
        if is_friday and parasha:
            shabbat_line = f"\nאיזה כיף - ערב שבת! פרשת השבוע: {parasha}."

        prompt = f"""אתה עוזר אישי לאישה דתייה בבני ברק. כתוב המלצות לבוש קצרות ואדיבות בעברית.

נתוני מזג האוויר להיום:
- טמפרטורה מקסימלית: {max_t}°C
- טמפרטורה מינימלית: {min_t}°C
- רוח מקסימלית: {wind} קמ"ש
- משקעים: {precip} מ"מ
{shabbat_line}

כללים חשובים:
- אם יש משקעים ביום שישי/שבת - אל תמליצי על מטרייה. המלצי על מעיל עמיד למים או כיסוי כובע
- כתבי 2-3 משפטים בלבד
- שמרי על טון חם ועידוד
- סיימי בברכה מתאימה לאותו יום"""

        clothing = await self._ask_gemini(prompt)
        if not clothing:
            clothing = self._fallback_clothing(max_t, precip, is_friday)

        return {"clothing_advice": clothing}

    # ------------------------------------------------------------------ #
    #  Alert email                                                         #
    # ------------------------------------------------------------------ #
    async def compose_alert(
        self,
        weather_data: Dict[str, Any],
        anomalies: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        anomaly_lines = "\n".join(f"- {a['message']}" for a in anomalies)

        prompt = f"""אתה עוזר אישי לאישה דתייה בבני ברק. כתוב הודעת התראה קצרה ואדיבה בעברית.

שינויים שזוהו במזג האוויר:
{anomaly_lines}

כללים:
- אל תמליצי על מטרייה בשבת
- כתבי 2-3 משפטים עם המלצה מעשית
- שמרי על טון רגוע וידידותי"""

        alert_text = await self._ask_gemini(prompt)
        if not alert_text:
            alert_text = "זוהו שינויים משמעותיים במזג האוויר. אנא התכוננו בהתאם ולבשו שכבות."

        return {"alert_text": alert_text}

    # ------------------------------------------------------------------ #
    #  Fallbacks (no API key)                                              #
    # ------------------------------------------------------------------ #
    def _fallback_clothing(
        self, max_temp: Optional[float], precip: Optional[float], is_friday: bool
    ) -> str:
        parts = []
        if max_temp is not None:
            if max_temp < 12:
                parts.append("קר מאוד - מומלץ מעיל חם, כובע וכפפות.")
            elif max_temp < 18:
                parts.append("קריר - קחי מעיל.")
            elif max_temp < 24:
                parts.append("מזג אוויר נעים - ג'קט קל מספיק.")
            else:
                parts.append("חם - לבוש קל יספיק.")

        if precip and precip > 0:
            if is_friday:
                parts.append("צפויים משקעים - מומלץ מעיל עמיד למים.")
            else:
                parts.append("צפויים משקעים - קחי מטרייה!")

        if is_friday:
            parts.append("שבת שלום ומבורכת!")
        else:
            parts.append("יום נפלא!")

        return " ".join(parts)
