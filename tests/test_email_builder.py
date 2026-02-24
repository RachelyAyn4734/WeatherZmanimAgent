"""Tests for EmailBuilder — HTML structure, content, and edge cases."""
import pytest
from datetime import datetime
import pytz
from agent.email_builder import EmailBuilder

ISRAEL_TZ = pytz.timezone("Asia/Jerusalem")


@pytest.fixture
def builder():
    return EmailBuilder()


@pytest.fixture
def now():
    return datetime(2026, 2, 23, 7, 0, 0, tzinfo=ISRAEL_TZ)


@pytest.fixture
def now_friday():
    return datetime(2026, 2, 27, 7, 0, 0, tzinfo=ISRAEL_TZ)  # Friday


# ------------------------------------------------------------------ #
#  Morning report                                                     #
# ------------------------------------------------------------------ #
class TestMorningReport:
    def test_returns_valid_html(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={"clothing_advice": "לבשי מעיל קל."},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert html.startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "</html>" in html

    def test_contains_greeting(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "בוקר טוב" in html

    def test_friday_greeting(self, builder, sample_weather_data, sample_zmanim_data, now_friday, sample_shabbat_data):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={"clothing_advice": "מעיל!"},
            is_friday=True,
            shabbat_data=sample_shabbat_data,
            parasha="פרשת תצוה",
            now=now_friday,
        )
        assert "שבת שלום" in html
        assert "פרשת תצוה" in html

    def test_shabbat_times_appear_on_friday(self, builder, sample_weather_data, sample_zmanim_data, now_friday, sample_shabbat_data):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=True,
            shabbat_data=sample_shabbat_data,
            parasha=None,
            now=now_friday,
        )
        assert "הדלקת נרות" in html
        assert "הבדלה" in html

    def test_no_shabbat_section_on_regular_day(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "הדלקת נרות" not in html

    def test_contains_zmanim(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "זריחה" in html
        assert "שקיעה" in html
        assert "חצות" in html

    def test_contains_temperature(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "19°" in html  # max temp from fixture
        assert "12°" in html  # min temp from fixture

    def test_clothing_advice_appears(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={"clothing_advice": "לבשי שכבות עם מגבעת!"},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "לבשי שכבות עם מגבעת!" in html

    def test_ten_day_forecast_present(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "תחזית 10 ימים" in html

    def test_footer_timestamp(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "SoulStream Weather Agent" in html
        assert "Open-Meteo" in html


# ------------------------------------------------------------------ #
#  Alert email                                                        #
# ------------------------------------------------------------------ #
class TestAlertEmail:
    def test_alert_email_valid_html(self, builder, sample_weather_data, now):
        anomalies = [
            {"type": "wind", "emoji": "💨", "message": 'רוחות חזקות: 45 קמ"ש'},
        ]
        html = builder.build_alert_email(
            weather_data=sample_weather_data,
            anomalies=anomalies,
            ai_content={"alert_text": "התכוני לרוחות!"},
            now=now,
        )
        assert "<!DOCTYPE html>" in html
        assert "התראת מזג אוויר" in html

    def test_alert_message_appears(self, builder, sample_weather_data, now):
        anomalies = [
            {"type": "fog", "emoji": "🌫️", "message": "אובך כבד: ראות 300 מטר"},
        ]
        html = builder.build_alert_email(
            weather_data=sample_weather_data,
            anomalies=anomalies,
            ai_content={},
            now=now,
        )
        assert "אובך כבד" in html
        assert "300" in html

    def test_multiple_anomalies_all_shown(self, builder, sample_weather_data, now):
        anomalies = [
            {"type": "wind",        "emoji": "💨",  "message": "רוחות חזקות: 50"},
            {"type": "fog",         "emoji": "🌫️", "message": "אובך כבד: 200מ"},
            {"type": "temperature", "emoji": "🌡️",  "message": "ירידה: 20→13"},
        ]
        html = builder.build_alert_email(
            weather_data=sample_weather_data,
            anomalies=anomalies,
            ai_content={"alert_text": "זהירות!"},
            now=now,
        )
        assert "רוחות חזקות" in html
        assert "אובך כבד" in html
        assert "ירידה" in html
        assert "זהירות" in html

    def test_ai_advice_shown(self, builder, sample_weather_data, now):
        anomalies = [{"type": "wind", "emoji": "💨", "message": "רוח"}]
        html = builder.build_alert_email(
            weather_data=sample_weather_data,
            anomalies=anomalies,
            ai_content={"alert_text": "הכניסי את הכביסה פנימה!"},
            now=now,
        )
        assert "הכניסי את הכביסה פנימה" in html

    def test_empty_ai_advice_no_crash(self, builder, sample_weather_data, now):
        anomalies = [{"type": "wind", "emoji": "💨", "message": "רוח"}]
        html = builder.build_alert_email(
            weather_data=sample_weather_data,
            anomalies=anomalies,
            ai_content={},
            now=now,
        )
        assert "<!DOCTYPE html>" in html


# ------------------------------------------------------------------ #
#  RTL and Hebrew content                                             #
# ------------------------------------------------------------------ #
class TestRTLContent:
    def test_html_dir_rtl(self, builder, sample_weather_data, sample_zmanim_data, now):
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert 'dir="rtl"' in html
        assert 'lang="he"' in html

    def test_no_umbrella_recommendation_on_friday(self, builder, sample_weather_data, sample_zmanim_data, now_friday, sample_shabbat_data):
        """On Friday, clothing advice from AI should not contain umbrella — this verifies
        the builder renders AI content as-is (umbrella filter is in AIComposer)."""
        advice = "לבשי מעיל גשם עמיד למים."  # correct Friday advice, no umbrella
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=sample_zmanim_data,
            ai_content={"clothing_advice": advice},
            is_friday=True,
            shabbat_data=sample_shabbat_data,
            parasha="פרשת תצוה",
            now=now_friday,
        )
        assert "מעיל גשם" in html
        assert "מטרייה" not in html


# ------------------------------------------------------------------ #
#  Edge cases with minimal / missing data                             #
# ------------------------------------------------------------------ #
class TestEdgeCases:
    def test_empty_daily_no_crash(self, builder, sample_zmanim_data, now):
        sparse_weather = {
            "hourly": {"time": [], "temperature_2m": [], "apparent_temperature": [],
                       "wind_speed_10m": [], "visibility": [],
                       "precipitation_probability": [], "precipitation": [],
                       "weather_code": [], "relative_humidity_2m": []},
            "daily": {"time": [], "temperature_2m_max": [], "temperature_2m_min": [],
                      "precipitation_sum": [], "precipitation_probability_max": [],
                      "wind_speed_10m_max": [], "weather_code": [],
                      "sunrise": [], "sunset": []},
        }
        html = builder.build_morning_report(
            weather_data=sparse_weather,
            zmanim_data=sample_zmanim_data,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "<!DOCTYPE html>" in html

    def test_empty_zmanim_no_crash(self, builder, sample_weather_data, now):
        empty_zmanim = {"times": {}}
        html = builder.build_morning_report(
            weather_data=sample_weather_data,
            zmanim_data=empty_zmanim,
            ai_content={},
            is_friday=False,
            shabbat_data=None,
            parasha=None,
            now=now,
        )
        assert "<!DOCTYPE html>" in html
