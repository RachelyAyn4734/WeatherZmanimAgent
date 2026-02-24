"""Tests for StateManager — save, load, edge cases."""
import json
import os
import pytest
import tempfile
from unittest.mock import patch
from agent.state import StateManager


@pytest.fixture
def tmp_state_file(tmp_path):
    """Returns a path to a temp state file and patches STATE_FILE."""
    state_path = str(tmp_path / "state.json")
    with patch("agent.state.STATE_FILE", state_path):
        yield state_path


# ------------------------------------------------------------------ #
#  Load tests                                                         #
# ------------------------------------------------------------------ #
class TestStateLoad:
    def test_returns_none_when_file_missing(self, tmp_state_file):
        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            result = manager.load()
        assert result is None

    def test_loads_valid_state(self, tmp_state_file, sample_weather_data):
        state = {
            "timestamp": "2026-02-23T07:00:00",
            "snapshot": {"temperature": 15.0, "wind_speed": 10.0},
        }
        with open(tmp_state_file, "w") as f:
            json.dump(state, f)

        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            result = manager.load()

        assert result is not None
        assert result["snapshot"]["temperature"] == 15.0

    def test_returns_none_on_corrupted_json(self, tmp_state_file):
        with open(tmp_state_file, "w") as f:
            f.write("{ this is not valid json !!!")

        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            result = manager.load()

        assert result is None  # should not raise

    def test_returns_none_on_empty_file(self, tmp_state_file):
        with open(tmp_state_file, "w") as f:
            f.write("")

        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            result = manager.load()

        assert result is None


# ------------------------------------------------------------------ #
#  Save tests                                                         #
# ------------------------------------------------------------------ #
class TestStateSave:
    def test_saves_file(self, tmp_state_file, sample_weather_data):
        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            manager.save(sample_weather_data)

        assert os.path.exists(tmp_state_file)

    def test_saved_file_is_valid_json(self, tmp_state_file, sample_weather_data):
        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            manager.save(sample_weather_data)

        with open(tmp_state_file) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "snapshot" in data

    def test_snapshot_contains_expected_keys(self, tmp_state_file, sample_weather_data):
        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            manager.save(sample_weather_data)

        with open(tmp_state_file) as f:
            data = json.load(f)

        snap = data["snapshot"]
        for key in ("temperature", "wind_speed", "visibility"):
            assert key in snap, f"Missing key: {key}"

    def test_overwrite_previous_state(self, tmp_state_file, sample_weather_data):
        """Saving twice should overwrite, not append."""
        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            manager.save(sample_weather_data)
            manager.save(sample_weather_data)

        with open(tmp_state_file) as f:
            content = f.read()

        # valid single JSON object, not two concatenated
        data = json.loads(content)
        assert isinstance(data, dict)


# ------------------------------------------------------------------ #
#  Round-trip                                                         #
# ------------------------------------------------------------------ #
class TestRoundTrip:
    def test_save_then_load_returns_same_data(self, tmp_state_file, sample_weather_data):
        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            manager.save(sample_weather_data)
            loaded = manager.load()

        assert loaded is not None
        assert "snapshot" in loaded
        assert loaded["snapshot"]["temperature"] is not None


# ------------------------------------------------------------------ #
#  Edge cases with empty/minimal weather data                        #
# ------------------------------------------------------------------ #
class TestStateSaveEdgeCases:
    def test_save_empty_weather_no_crash(self, tmp_state_file):
        empty_weather = {"hourly": {"time": [], "temperature_2m": []}}
        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            manager.save(empty_weather)  # should not raise

    def test_save_weather_with_none_values(self, tmp_state_file):
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
        with patch("agent.state.STATE_FILE", tmp_state_file):
            manager = StateManager()
            manager.save(weather)  # should not raise

        with open(tmp_state_file) as f:
            data = json.load(f)
        assert data["snapshot"]["temperature"] is None
