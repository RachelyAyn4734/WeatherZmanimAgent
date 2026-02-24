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
        subject = f"[Rachely] דוח בוקר - {date_str}"
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


if __name__ == "__main__":
    asyncio.run(run_agent())
