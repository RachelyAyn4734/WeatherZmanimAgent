"""Tests for AlertDetector — covers all edge cases."""
import pytest
from agent.alerts import AlertDetector, WIND_THRESHOLD_KMH, FOG_VISIBILITY_THRESHOLD_M, TEMP_CHANGE_THRESHOLD_C


@pytest.fixture
def detector():
    return AlertDetector()


# Helper — builds minimal weather_data with one hourly slot at index 0
def make_weather(temp=15.0, wind=10.0, visibility=10000, hour="2026-02-23T07:00"):
    return {
        "hourly": {
            "time":                     [hour],
            "temperature_2m":           [temp],
            "wind_speed_10m":           [wind],
            "visibility":               [visibility],
            "precipitation_probability": [5],
            "weather_code":             [1],
        }
    }


def make_state(temp=15.0, wind=10.0):
    return {
        "timestamp": "2026-02-23T04:00:00",
        "snapshot": {
            "time": "2026-02-23T04:00",
            "temperature": temp,
            "wind_speed": wind,
            "visibility": 10000,
            "precipitation_probability": 5,
            "weather_code": 1,
        },
    }


# ------------------------------------------------------------------ #
#  Wind tests                                                         #
# ------------------------------------------------------------------ #
class TestWindAlerts:
    def test_no_alert_below_threshold(self, detector):
        weather = make_weather(wind=WIND_THRESHOLD_KMH - 1)
        anomalies = detector.detect(weather, None)
        wind_alerts = [a for a in anomalies if a["type"] == "wind"]
        assert len(wind_alerts) == 0

    def test_alert_exactly_at_threshold(self, detector):
        """Strictly above threshold triggers alert."""
        weather = make_weather(wind=WIND_THRESHOLD_KMH)
        anomalies = detector.detect(weather, None)
        wind_alerts = [a for a in anomalies if a["type"] == "wind"]
        assert len(wind_alerts) == 0  # threshold is >, not >=

    def test_alert_above_threshold(self, detector):
        weather = make_weather(wind=WIND_THRESHOLD_KMH + 1)
        anomalies = detector.detect(weather, None)
        wind_alerts = [a for a in anomalies if a["type"] == "wind"]
        assert len(wind_alerts) == 1
        assert "קמ" in wind_alerts[0]["message"]

    def test_extreme_wind(self, detector):
        weather = make_weather(wind=90.0)
        anomalies = detector.detect(weather, None)
        wind_alerts = [a for a in anomalies if a["type"] == "wind"]
        assert len(wind_alerts) == 1
        assert "90" in wind_alerts[0]["message"]


# ------------------------------------------------------------------ #
#  Fog / visibility tests                                             #
# ------------------------------------------------------------------ #
class TestFogAlerts:
    def test_no_alert_good_visibility(self, detector):
        weather = make_weather(visibility=FOG_VISIBILITY_THRESHOLD_M + 1)
        anomalies = detector.detect(weather, None)
        assert not any(a["type"] == "fog" for a in anomalies)

    def test_alert_heavy_fog(self, detector):
        weather = make_weather(visibility=500)
        anomalies = detector.detect(weather, None)
        fog_alerts = [a for a in anomalies if a["type"] == "fog"]
        assert len(fog_alerts) == 1
        assert "500" in fog_alerts[0]["message"]

    def test_alert_zero_visibility(self, detector):
        weather = make_weather(visibility=0)
        anomalies = detector.detect(weather, None)
        assert any(a["type"] == "fog" for a in anomalies)

    def test_boundary_visibility_exact_threshold(self, detector):
        """Exactly at threshold = still fog alert (< not <=)."""
        weather = make_weather(visibility=FOG_VISIBILITY_THRESHOLD_M)
        anomalies = detector.detect(weather, None)
        assert not any(a["type"] == "fog" for a in anomalies)


# ------------------------------------------------------------------ #
#  Temperature change tests                                           #
# ------------------------------------------------------------------ #
class TestTemperatureAlerts:
    def test_no_alert_small_change(self, detector):
        weather = make_weather(temp=16.0)
        state = make_state(temp=15.0)  # 1 degree diff
        anomalies = detector.detect(weather, state)
        assert not any(a["type"] == "temperature" for a in anomalies)

    def test_alert_large_increase(self, detector):
        weather = make_weather(temp=22.0)
        state = make_state(temp=15.0)  # +7 degrees
        anomalies = detector.detect(weather, state)
        temp_alerts = [a for a in anomalies if a["type"] == "temperature"]
        assert len(temp_alerts) == 1
        assert "עלייה" in temp_alerts[0]["message"]

    def test_alert_large_decrease(self, detector):
        weather = make_weather(temp=8.0)
        state = make_state(temp=15.0)  # -7 degrees
        anomalies = detector.detect(weather, state)
        temp_alerts = [a for a in anomalies if a["type"] == "temperature"]
        assert len(temp_alerts) == 1
        assert "ירידה" in temp_alerts[0]["message"]

    def test_no_alert_without_previous_state(self, detector):
        weather = make_weather(temp=30.0)
        anomalies = detector.detect(weather, None)
        assert not any(a["type"] == "temperature" for a in anomalies)

    def test_no_alert_exact_threshold(self, detector):
        """Exactly 5 degrees change should NOT trigger (> not >=)."""
        weather = make_weather(temp=20.0)
        state = make_state(temp=15.0)
        anomalies = detector.detect(weather, state)
        assert not any(a["type"] == "temperature" for a in anomalies)


# ------------------------------------------------------------------ #
#  Multiple anomalies                                                 #
# ------------------------------------------------------------------ #
class TestMultipleAnomalies:
    def test_wind_and_fog_together(self, detector):
        weather = make_weather(wind=50.0, visibility=200)
        anomalies = detector.detect(weather, None)
        types = [a["type"] for a in anomalies]
        assert "wind" in types
        assert "fog" in types
        assert len(anomalies) == 2

    def test_all_three_anomalies(self, detector):
        weather = make_weather(wind=50.0, visibility=200, temp=25.0)
        state = make_state(temp=15.0)
        anomalies = detector.detect(weather, state)
        types = [a["type"] for a in anomalies]
        assert "wind" in types
        assert "fog" in types
        assert "temperature" in types
        assert len(anomalies) == 3

    def test_no_anomalies_normal_conditions(self, detector):
        weather = make_weather(wind=10.0, visibility=10000, temp=18.0)
        state = make_state(temp=17.0)
        anomalies = detector.detect(weather, state)
        assert anomalies == []


# ------------------------------------------------------------------ #
#  Robustness / missing data                                          #
# ------------------------------------------------------------------ #
class TestRobustness:
    def test_none_values_in_hourly(self, detector):
        """Should not crash if hourly values are None."""
        weather = {
            "hourly": {
                "time": ["2026-02-23T07:00"],
                "temperature_2m": [None],
                "wind_speed_10m": [None],
                "visibility": [None],
                "precipitation_probability": [None],
                "weather_code": [None],
            }
        }
        anomalies = detector.detect(weather, None)
        assert isinstance(anomalies, list)

    def test_empty_hourly(self, detector):
        """Should not crash with empty hourly data."""
        weather = {"hourly": {"time": [], "temperature_2m": [], "wind_speed_10m": [], "visibility": []}}
        anomalies = detector.detect(weather, None)
        assert isinstance(anomalies, list)

    def test_corrupted_previous_state(self, detector):
        """Should not crash with malformed previous state."""
        weather = make_weather(temp=20.0)
        bad_state = {"timestamp": "2026-01-01", "snapshot": {}}  # missing temp key
        anomalies = detector.detect(weather, bad_state)
        assert isinstance(anomalies, list)
