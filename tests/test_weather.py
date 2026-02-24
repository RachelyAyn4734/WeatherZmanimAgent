"""Tests for WeatherClient static helpers — WMO codes, emojis."""
import pytest
from agent.weather import WeatherClient


class TestWMODescriptions:
    def test_clear_sky(self):
        assert WeatherClient.code_to_description(0) == "שמיים בהירים"

    def test_overcast(self):
        assert WeatherClient.code_to_description(3) == "מעונן"

    def test_fog(self):
        assert "ערפל" in WeatherClient.code_to_description(45)

    def test_light_rain(self):
        assert WeatherClient.code_to_description(61) == "גשם קל"

    def test_heavy_rain(self):
        assert WeatherClient.code_to_description(65) == "גשם כבד"

    def test_thunderstorm(self):
        assert "סופת" in WeatherClient.code_to_description(95)

    def test_unknown_code_returns_fallback(self):
        result = WeatherClient.code_to_description(999)
        assert result == "לא ידוע"

    def test_snow(self):
        assert "שלג" in WeatherClient.code_to_description(71)


class TestWMOEmojis:
    def test_clear_sky_emoji(self):
        assert WeatherClient.code_to_emoji(0) == "☀️"

    def test_partly_cloudy_emoji(self):
        assert WeatherClient.code_to_emoji(2) == "⛅"

    def test_rain_emoji(self):
        emoji = WeatherClient.code_to_emoji(63)
        assert emoji in ("🌧️", "🌦️")

    def test_thunderstorm_emoji(self):
        assert WeatherClient.code_to_emoji(95) == "⛈️"

    def test_fog_emoji(self):
        assert WeatherClient.code_to_emoji(45) == "🌫️"

    def test_unknown_code_returns_fallback_emoji(self):
        result = WeatherClient.code_to_emoji(999)
        assert result == "🌡️"

    def test_all_known_codes_return_string(self):
        known_codes = [0, 1, 2, 3, 45, 48, 51, 53, 55, 61, 63, 65,
                       71, 73, 75, 80, 81, 82, 95, 96]
        for code in known_codes:
            assert isinstance(WeatherClient.code_to_emoji(code), str)
            assert isinstance(WeatherClient.code_to_description(code), str)
