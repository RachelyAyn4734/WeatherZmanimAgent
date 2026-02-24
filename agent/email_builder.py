"""HTML email builder with beautiful inline-CSS templates."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import pytz

from .weather import WeatherClient
from .zmanim import ZmanimClient

log = logging.getLogger(__name__)

ISRAEL_TZ = pytz.timezone("Asia/Jerusalem")

# Primary palette
COLOR_BG = "#f4f7fb"
COLOR_CARD = "#ffffff"
COLOR_HEADER = "#1a3a5c"
COLOR_ACCENT = "#3a7bd5"
COLOR_GOLD = "#c9a84c"
COLOR_TEXT = "#333333"
COLOR_MUTED = "#888888"
COLOR_ALERT = "#e53935"
COLOR_GREEN = "#2e7d32"

DAY_NAMES_HE = {
    0: "שני", 1: "שלישי", 2: "רביעי",
    3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון",
}

MONTH_NAMES_HE = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל",
    5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט",
    9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
}


def _base_style() -> str:
    return """
    body { margin:0; padding:0; background:#f4f7fb; font-family: 'Segoe UI', Arial, sans-serif; direction:rtl; }
    .wrapper { max-width:640px; margin:0 auto; background:#f4f7fb; padding:20px 10px; }
    .card { background:#fff; border-radius:16px; box-shadow:0 2px 12px rgba(0,0,0,.08); margin-bottom:16px; overflow:hidden; }
    .card-header { padding:18px 24px; color:#fff; }
    .card-body { padding:20px 24px; }
    table { border-collapse:collapse; width:100%; }
    td, th { padding:8px 12px; font-size:14px; }
    th { background:#eef2f8; color:#1a3a5c; font-weight:600; }
    tr:nth-child(even) td { background:#f9fbff; }
    .badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
    .footer { text-align:center; font-size:12px; color:#aaa; padding:12px; }
    """


def _format_date_he(d: date) -> str:
    day_heb = DAY_NAMES_HE[d.weekday()]
    month_heb = MONTH_NAMES_HE[d.month]
    return f"יום {day_heb}, {d.day} ב{month_heb} {d.year}"


def _get_hourly_slice(weather_data: Dict, hours: int = 24) -> List[Dict]:
    """Return up to `hours` hourly records starting from the current hour."""
    hourly = weather_data.get("hourly", {})
    times = hourly.get("time", [])
    now_str = datetime.now(ISRAEL_TZ).strftime("%Y-%m-%dT%H:00")

    start = 0
    if now_str in times:
        start = times.index(now_str)

    result = []
    for i in range(start, min(start + hours, len(times))):
        result.append({
            "time": times[i][11:16] if len(times[i]) >= 16 else times[i],
            "temp": hourly.get("temperature_2m", [])[i] if i < len(hourly.get("temperature_2m", [])) else None,
            "feels": hourly.get("apparent_temperature", [])[i] if i < len(hourly.get("apparent_temperature", [])) else None,
            "wind": hourly.get("wind_speed_10m", [])[i] if i < len(hourly.get("wind_speed_10m", [])) else None,
            "precip_prob": hourly.get("precipitation_probability", [])[i] if i < len(hourly.get("precipitation_probability", [])) else None,
            "code": hourly.get("weather_code", [])[i] if i < len(hourly.get("weather_code", [])) else 0,
        })
    return result


class EmailBuilder:

    # ------------------------------------------------------------------ #
    #  MORNING REPORT                                                      #
    # ------------------------------------------------------------------ #
    def build_morning_report(
        self,
        weather_data: Dict[str, Any],
        zmanim_data: Dict[str, Any],
        ai_content: Dict[str, str],
        is_friday: bool,
        shabbat_data: Optional[Dict[str, Any]],
        parasha: Optional[str],
        now: datetime,
    ) -> str:
        date_he = _format_date_he(now.date())
        greeting = "שבת שלום!" if is_friday else "בוקר טוב!"

        sections = [
            self._header_section(greeting, date_he, parasha),
            self._today_summary_section(weather_data),
            self._clothing_section(ai_content.get("clothing_advice", "")),
            self._hourly_section(weather_data),
            self._zmanim_section(zmanim_data),
        ]

        if is_friday and shabbat_data:
            sections.append(self._shabbat_section(shabbat_data))

        sections.append(self._ten_day_section(weather_data))
        sections.append(self._footer_section(now))

        return self._wrap(sections)

    # ------------------------------------------------------------------ #
    #  ALERT EMAIL                                                         #
    # ------------------------------------------------------------------ #
    def build_alert_email(
        self,
        weather_data: Dict[str, Any],
        anomalies: List[Dict],
        ai_content: Dict[str, str],
        now: datetime,
    ) -> str:
        date_he = _format_date_he(now.date())

        sections = [
            self._alert_header_section(anomalies, date_he),
            self._anomaly_list_section(anomalies),
            self._alert_advice_section(ai_content.get("alert_text", "")),
            self._today_summary_section(weather_data),
            self._footer_section(now),
        ]

        return self._wrap(sections)

    # ------------------------------------------------------------------ #
    #  Section builders                                                    #
    # ------------------------------------------------------------------ #
    def _wrap(self, sections: List[str]) -> str:
        style = _base_style()
        body = "\n".join(sections)
        return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>{style}</style>
</head>
<body>
  <div class="wrapper">{body}</div>
</body>
</html>"""

    def _header_section(self, greeting: str, date_he: str, parasha: Optional[str]) -> str:
        parasha_line = (
            f'<p style="margin:6px 0 0;font-size:15px;opacity:.9;">פרשת השבוע: {parasha}</p>'
            if parasha else ""
        )
        return f"""
<div class="card">
  <div class="card-header" style="background:linear-gradient(135deg,{COLOR_HEADER},{COLOR_ACCENT});text-align:center;">
    <p style="margin:0;font-size:28px;">🌤️ {greeting}</p>
    <p style="margin:6px 0 0;font-size:14px;opacity:.85;">{date_he}</p>
    <p style="margin:4px 0 0;font-size:13px;opacity:.8;">בני ברק, ישראל</p>
    {parasha_line}
  </div>
</div>"""

    def _today_summary_section(self, weather_data: Dict) -> str:
        daily = weather_data.get("daily", {})
        max_t = (daily.get("temperature_2m_max") or [None])[0]
        min_t = (daily.get("temperature_2m_min") or [None])[0]
        wind = (daily.get("wind_speed_10m_max") or [None])[0]
        precip = (daily.get("precipitation_sum") or [None])[0]
        precip_prob = (daily.get("precipitation_probability_max") or [None])[0]
        code = (daily.get("weather_code") or [0])[0] or 0
        sunrise = ((daily.get("sunrise") or [""])[0] or "")[11:16]
        sunset = ((daily.get("sunset") or [""])[0] or "")[11:16]
        emoji = WeatherClient.code_to_emoji(code)
        desc = WeatherClient.code_to_description(code)

        max_str = f"{max_t:.0f}°" if max_t is not None else "—"
        min_str = f"{min_t:.0f}°" if min_t is not None else "—"
        wind_str = f'{wind:.0f} קמ"ש' if wind is not None else "—"
        precip_str = f"{precip:.1f} מ\"מ" if precip is not None else "—"
        precip_prob_str = f"{precip_prob:.0f}%" if precip_prob is not None else "—"

        return f"""
<div class="card">
  <div class="card-header" style="background:{COLOR_ACCENT};">
    <p style="margin:0;font-size:16px;font-weight:600;text-align:center;">תחזית היום</p>
  </div>
  <div class="card-body">
    <div style="text-align:center;margin-bottom:16px;">
      <span style="font-size:48px;">{emoji}</span>
      <p style="margin:4px 0;font-size:17px;font-weight:600;color:{COLOR_TEXT};">{desc}</p>
    </div>
    <table>
      <tr>
        <td style="font-weight:600;color:{COLOR_HEADER};">🌡️ טמפרטורה</td>
        <td>{max_str} / {min_str}</td>
        <td style="font-weight:600;color:{COLOR_HEADER};">💨 רוח</td>
        <td>{wind_str}</td>
      </tr>
      <tr>
        <td style="font-weight:600;color:{COLOR_HEADER};">🌧️ משקעים</td>
        <td>{precip_str} ({precip_prob_str})</td>
        <td style="font-weight:600;color:{COLOR_HEADER};">☀️ זריחה / שקיעה</td>
        <td>{sunrise} / {sunset}</td>
      </tr>
    </table>
  </div>
</div>"""

    def _clothing_section(self, advice: str) -> str:
        if not advice:
            return ""
        return f"""
<div class="card">
  <div class="card-header" style="background:{COLOR_GOLD};">
    <p style="margin:0;font-size:16px;font-weight:600;text-align:center;">👗 המלצות לבוש</p>
  </div>
  <div class="card-body">
    <p style="margin:0;font-size:15px;line-height:1.7;color:{COLOR_TEXT};">{advice}</p>
  </div>
</div>"""

    def _hourly_section(self, weather_data: Dict) -> str:
        rows = ""
        for h in _get_hourly_slice(weather_data, 12):
            emoji = WeatherClient.code_to_emoji(h["code"])
            temp = f'{h["temp"]:.0f}°' if h["temp"] is not None else "—"
            wind = f'{h["wind"]:.0f}' if h["wind"] is not None else "—"
            prob = f'{h["precip_prob"]:.0f}%' if h["precip_prob"] is not None else "—"
            rows += f"""<tr>
              <td style="font-weight:600;">{h["time"]}</td>
              <td>{emoji}</td>
              <td>{temp}</td>
              <td>{wind} קמ"ש</td>
              <td>{prob}</td>
            </tr>"""

        return f"""
<div class="card">
  <div class="card-header" style="background:{COLOR_HEADER};">
    <p style="margin:0;font-size:16px;font-weight:600;text-align:center;">⏰ תחזית שעתית (12 שעות)</p>
  </div>
  <div class="card-body" style="padding:0;">
    <table>
      <thead><tr>
        <th>שעה</th><th>מזג</th><th>טמפ'</th><th>רוח</th><th>גשם</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""

    def _zmanim_section(self, zmanim_data: Dict) -> str:
        SHOW_KEYS = [
            "alotHaShachar", "sunrise", "sofZmanShma",
            "chatzot", "minchaGedola", "plagHaMincha",
            "sunset", "tzeit7083deg",
        ]
        times = zmanim_data.get("times", {})
        rows = ""
        for key in SHOW_KEYS:
            if key in times:
                label = ZmanimClient.get_label(key)
                time_str = ZmanimClient.extract_time(zmanim_data, key) or "—"
                rows += f"<tr><td style='font-weight:600;'>{label}</td><td>{time_str}</td></tr>"

        if not rows:
            return ""

        return f"""
<div class="card">
  <div class="card-header" style="background:#2c3e50;">
    <p style="margin:0;font-size:16px;font-weight:600;text-align:center;">🕍 זמני היום - בני ברק</p>
  </div>
  <div class="card-body" style="padding:0;">
    <table><tbody>{rows}</tbody></table>
  </div>
</div>"""

    def _shabbat_section(self, shabbat_data: Dict) -> str:
        items = shabbat_data.get("items", [])
        candles = havdalah = title = ""
        for item in items:
            cat = item.get("category", "")
            if cat == "candles":
                candles = item.get("date", "")[-14:-9] if item.get("date") else ""
            elif cat == "havdalah":
                havdalah = item.get("date", "")[-14:-9] if item.get("date") else ""
            elif cat == "parashat":
                title = item.get("hebrew") or item.get("title", "")

        return f"""
<div class="card">
  <div class="card-header" style="background:linear-gradient(135deg,#4a148c,{COLOR_GOLD});">
    <p style="margin:0;font-size:16px;font-weight:600;text-align:center;">🕯️ כניסת שבת - {title}</p>
  </div>
  <div class="card-body">
    <table>
      <tr>
        <td style="font-weight:600;font-size:16px;color:{COLOR_HEADER};">🕯️ הדלקת נרות</td>
        <td style="font-size:18px;font-weight:700;color:{COLOR_ACCENT};">{candles or '—'}</td>
      </tr>
      <tr>
        <td style="font-weight:600;font-size:16px;color:{COLOR_HEADER};">✨ צאת שבת (הבדלה)</td>
        <td style="font-size:18px;font-weight:700;color:{COLOR_ACCENT};">{havdalah or '—'}</td>
      </tr>
    </table>
  </div>
</div>"""

    def _ten_day_section(self, weather_data: Dict) -> str:
        daily = weather_data.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        codes = daily.get("weather_code", [])
        precips = daily.get("precipitation_sum", [])
        precip_probs = daily.get("precipitation_probability_max", [])

        rows = ""
        for i, d_str in enumerate(dates):
            try:
                d = date.fromisoformat(d_str)
                day_heb = DAY_NAMES_HE[d.weekday()]
                date_display = f"{day_heb} {d.day}/{d.month}"
            except Exception:
                date_display = d_str

            code = codes[i] if i < len(codes) else 0
            emoji = WeatherClient.code_to_emoji(code or 0)
            max_t = f'{max_temps[i]:.0f}°' if i < len(max_temps) and max_temps[i] is not None else "—"
            min_t = f'{min_temps[i]:.0f}°' if i < len(min_temps) and min_temps[i] is not None else "—"
            precip = precips[i] if i < len(precips) and precips[i] is not None else 0
            prob = precip_probs[i] if i < len(precip_probs) and precip_probs[i] is not None else 0
            precip_str = f"{precip:.0f}מ\"מ ({prob:.0f}%)" if precip > 0 else "יבש"
            row_bg = "#fff8e1" if d.weekday() == 4 else ""  # highlight Friday

            rows += f"""<tr style="background:{row_bg};">
              <td style="font-weight:600;">{date_display}</td>
              <td style="font-size:18px;">{emoji}</td>
              <td style="color:#c62828;">{max_t}</td>
              <td style="color:{COLOR_ACCENT};">{min_t}</td>
              <td>{precip_str}</td>
            </tr>"""

        return f"""
<div class="card">
  <div class="card-header" style="background:{COLOR_HEADER};">
    <p style="margin:0;font-size:16px;font-weight:600;text-align:center;">📅 תחזית 10 ימים</p>
  </div>
  <div class="card-body" style="padding:0;">
    <table>
      <thead><tr>
        <th>יום</th><th>מזג</th><th>מקס'</th><th>מינ'</th><th>משקעים</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""

    def _alert_header_section(self, anomalies: List[Dict], date_he: str) -> str:
        count = len(anomalies)
        return f"""
<div class="card">
  <div class="card-header" style="background:linear-gradient(135deg,{COLOR_ALERT},#ff6f00);text-align:center;">
    <p style="margin:0;font-size:26px;">⚠️ התראת מזג אוויר</p>
    <p style="margin:6px 0 0;font-size:14px;opacity:.9;">{date_he}</p>
    <p style="margin:4px 0 0;font-size:13px;opacity:.85;">זוהו {count} שינויים חריגים</p>
  </div>
</div>"""

    def _anomaly_list_section(self, anomalies: List[Dict]) -> str:
        items_html = ""
        for a in anomalies:
            items_html += f"""
<div style="background:#fff3f3;border-right:4px solid {COLOR_ALERT};padding:12px 16px;margin-bottom:10px;border-radius:8px;">
  <span style="font-size:20px;">{a.get('emoji','⚠️')}</span>
  <span style="font-weight:600;font-size:15px;margin-right:8px;color:{COLOR_ALERT};">{a['message']}</span>
</div>"""

        return f"""
<div class="card">
  <div class="card-header" style="background:{COLOR_ALERT};">
    <p style="margin:0;font-size:16px;font-weight:600;text-align:center;">פירוט השינויים</p>
  </div>
  <div class="card-body">{items_html}</div>
</div>"""

    def _alert_advice_section(self, advice: str) -> str:
        if not advice:
            return ""
        return f"""
<div class="card">
  <div class="card-header" style="background:{COLOR_GOLD};">
    <p style="margin:0;font-size:16px;font-weight:600;text-align:center;">💡 המלצה</p>
  </div>
  <div class="card-body">
    <p style="margin:0;font-size:15px;line-height:1.7;color:{COLOR_TEXT};">{advice}</p>
  </div>
</div>"""

    def _footer_section(self, now: datetime) -> str:
        ts = now.strftime("%d/%m/%Y %H:%M")
        return f"""
<div class="footer">
  <p>נשלח ע"י Rachely Weather Agent | {ts} שעון ישראל</p>
  <p>נתוני מזג אוויר: Open-Meteo | זמנים: Hebcal | AI: Gemini</p>
</div>"""
