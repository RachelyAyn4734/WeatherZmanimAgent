#!/usr/bin/env python3
"""
Smart Weather & Zmanim Agent for Bnei Brak
Runs every 3 hours via GitHub Actions.
- 07:00 Israel time: sends full morning report
- Every 3 hours: checks for unusual weather changes and sends alerts
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
import pytz

from agent.weather import WeatherClient
from agent.zmanim import ZmanimClient
from agent.state import StateManager
from agent.email_builder import EmailBuilder
from agent.ai_composer import AIComposer
from agent.alerts import AlertDetector
from agent.sender import EmailSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

ISRAEL_TZ = pytz.timezone("Asia/Jerusalem")
BNEI_BRAK_LAT = 32.0840
BNEI_BRAK_LON = 34.8337

# Morning report hour in Israel local time (handles both IST and IDT)
MORNING_HOURS = {7, 8}  # 7 in winter (UTC+2), 8 in summer (UTC+3)


async def run_agent():
    now_israel = datetime.now(ISRAEL_TZ)
    hour = now_israel.hour
    weekday = now_israel.weekday()  # 0=Mon … 5=Sat, 6=Sun
    is_friday = weekday == 4
    is_morning = hour in MORNING_HOURS

    # Allow forcing morning report for manual testing
    force_morning = os.environ.get("FORCE_MORNING", "").lower() in ("1", "true", "yes")
    if force_morning:
        is_morning = True
        log.info("FORCE_MORNING is set — overriding to morning report mode")

    log.info(
        "Agent running at %s Israel time | hour=%d | friday=%s | morning=%s",
        now_israel.strftime("%Y-%m-%d %H:%M"),
        hour,
        is_friday,
        is_morning,
    )

    # --- Initialise clients ---
    weather_client = WeatherClient(BNEI_BRAK_LAT, BNEI_BRAK_LON)
    zmanim_client = ZmanimClient(BNEI_BRAK_LAT, BNEI_BRAK_LON)
    state_manager = StateManager()
    ai_composer = AIComposer()
    email_builder = EmailBuilder()
    email_sender = EmailSender()
    alert_detector = AlertDetector()

    # --- Fetch data ---
    log.info("Fetching weather data from Open-Meteo...")
    weather_data = await weather_client.get_full_forecast()

    log.info("Fetching zmanim from Hebcal...")
    zmanim_data = await zmanim_client.get_zmanim(now_israel.date())

    # --- State management ---
    previous_state = state_manager.load()
    state_manager.save(weather_data)

    # ------------------------------------------------------------------ #
    #  MORNING REPORT                                                      #
    # ------------------------------------------------------------------ #
    if is_morning:
        log.info("Composing morning report...")

        shabbat_data = None
        parasha = await zmanim_client.get_weekly_parasha(now_israel.date())

        if is_friday:
            log.info("Friday detected - fetching Shabbat times...")
            shabbat_data = await zmanim_client.get_shabbat_times(now_israel.date())

        ai_content = await ai_composer.compose_morning_report(
            weather_data=weather_data,
            zmanim_data=zmanim_data,
            is_friday=is_friday,
            shabbat_data=shabbat_data,
            parasha=parasha,
        )

        html_body = email_builder.build_morning_report(
            weather_data=weather_data,
            zmanim_data=zmanim_data,
            ai_content=ai_content,
            is_friday=is_friday,
            shabbat_data=shabbat_data,
            parasha=parasha,
            now=now_israel,
        )

        date_str = now_israel.strftime("%d/%m/%Y")
        subject = f"תחזית מזג אוויר וזמני היום - {date_str}"
        if is_friday:
            subject += " | שבת שלום!"

        success = await email_sender.send(subject, html_body)
        if success:
            log.info("Morning report sent successfully.")
        else:
            log.error("Failed to send morning report.")
            sys.exit(1)

    # ------------------------------------------------------------------ #
    #  ANOMALY CHECK (every 3 hours)                                       #
    # ------------------------------------------------------------------ #
    else:
        log.info("Checking for weather anomalies...")
        anomalies = alert_detector.detect(weather_data, previous_state)

        if anomalies:
            log.info("Anomalies detected: %s", [a["type"] for a in anomalies])

            ai_content = await ai_composer.compose_alert(weather_data, anomalies)

            html_body = email_builder.build_alert_email(
                weather_data=weather_data,
                anomalies=anomalies,
                ai_content=ai_content,
                now=now_israel,
            )

            dt_str = now_israel.strftime("%d/%m/%Y %H:%M")
            subject = f"[Rachely] התראת מזג אוויר - {dt_str}"

            success = await email_sender.send(subject, html_body)
            if success:
                log.info("Weather alert sent.")
            else:
                log.error("Failed to send weather alert.")
                sys.exit(1)
        else:
            log.info("No anomalies detected. No email sent.")




async def run_full_test():
    """Send both morning report AND a test alert email immediately.

    Triggered by FORCE_TEST=1 (locally or via GitHub Actions workflow_dispatch).
    Uses live weather / zmanim data plus dummy anomalies for the alert.
    """
    now_israel = datetime.now(ISRAEL_TZ)
    log.info("=== TEST MODE: sending morning report + alert email ===")

    weather_client = WeatherClient(BNEI_BRAK_LAT, BNEI_BRAK_LON)
    zmanim_client  = ZmanimClient(BNEI_BRAK_LAT, BNEI_BRAK_LON)
    ai_composer    = AIComposer()
    email_builder  = EmailBuilder()
    email_sender   = EmailSender()

    log.info("[TEST] Fetching live weather & zmanim data...")
    weather_data = await weather_client.get_full_forecast()
    zmanim_data  = await zmanim_client.get_zmanim(now_israel.date())
    parasha      = await zmanim_client.get_weekly_parasha(now_israel.date())

    is_friday    = now_israel.weekday() == 4
    shabbat_data = None
    if is_friday:
        shabbat_data = await zmanim_client.get_shabbat_times(now_israel.date())

    # ---- Morning report ----
    log.info("[TEST] Composing morning report...")
    ai_morning = await ai_composer.compose_morning_report(
        weather_data=weather_data,
        zmanim_data=zmanim_data,
        is_friday=is_friday,
        shabbat_data=shabbat_data,
        parasha=parasha,
    )
    html_morning = email_builder.build_morning_report(
        weather_data=weather_data,
        zmanim_data=zmanim_data,
        ai_content=ai_morning,
        is_friday=is_friday,
        shabbat_data=shabbat_data,
        parasha=parasha,
        now=now_israel,
    )
    date_str = now_israel.strftime("%d/%m/%Y")
    subject_morning = f"[TEST] תחזית מזג אוויר וזמנים היום - {date_str}"
    ok1 = await email_sender.send(subject_morning, html_morning)
    log.info("[TEST] Morning report %s.", "sent" if ok1 else "FAILED")

    # ---- Alert email with dummy anomalies ----
    log.info("[TEST] Composing alert email (dummy anomalies)...")
    dummy_anomalies = [
        {
            "type": "wind", "current": 45, "threshold": 30, "emoji": "\U0001f4a8",
            "message": "רוחות חזקות: 45 קמ\"ש (סף: 30) \u2014 TEST",
        },
        {
            "type": "temperature", "current": 28, "previous": 21, "diff": 7,
            "emoji": "\U0001f321\ufe0f",
            "message": "עלייה חדה בטמפרטורה: 21\u00b0C \u2192 28\u00b0C (7.0\u00b0 שינוי) \u2014 TEST",
        },
    ]
    ai_alert   = await ai_composer.compose_alert(weather_data, dummy_anomalies)
    html_alert = email_builder.build_alert_email(
        weather_data=weather_data,
        anomalies=dummy_anomalies,
        ai_content=ai_alert,
        now=now_israel,
    )
    dt_str = now_israel.strftime("%d/%m/%Y %H:%M")
    subject_alert = f"[TEST] התראת מזג אוויר - {dt_str}"
    ok2 = await email_sender.send(subject_alert, html_alert)
    log.info("[TEST] Alert email %s.", "sent" if ok2 else "FAILED")

    log.info("=== TEST MODE complete | Morning=%s  Alert=%s ===", ok1, ok2)
    if not (ok1 and ok2):
        sys.exit(1)


if __name__ == "__main__":
    _force_test = os.environ.get("FORCE_TEST", "").lower() in ("1", "true", "yes")
    if _force_test:
        asyncio.run(run_full_test())
    else:
        asyncio.run(run_agent())

