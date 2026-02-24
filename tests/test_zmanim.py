"""Tests for ZmanimClient static helpers."""
import pytest
from agent.zmanim import ZmanimClient, ZMANIM_LABELS_HE


class TestExtractTime:
    def test_extracts_correct_hhmm(self):
        data = {"times": {"sunrise": "2026-02-23T06:15:00+02:00"}}
        result = ZmanimClient.extract_time(data, "sunrise")
        assert result == "06:15"

    def test_extracts_time_with_midnight(self):
        data = {"times": {"chatzotLayla": "2026-02-24T00:30:00+02:00"}}
        result = ZmanimClient.extract_time(data, "chatzotLayla")
        assert result == "00:30"

    def test_returns_none_for_missing_key(self):
        data = {"times": {}}
        result = ZmanimClient.extract_time(data, "sunrise")
        assert result is None

    def test_returns_none_for_missing_times_key(self):
        data = {}
        result = ZmanimClient.extract_time(data, "sunrise")
        assert result is None

    def test_handles_all_sample_zmanim_keys(self, sample_zmanim_data):
        keys = ["alotHaShachar", "sunrise", "chatzot", "sunset", "tzeit7083deg"]
        for key in keys:
            result = ZmanimClient.extract_time(sample_zmanim_data, key)
            assert result is not None, f"Expected time for {key}"
            assert len(result) == 5, f"Expected HH:MM format for {key}, got {result}"
            assert result[2] == ":", f"Expected colon at position 2 for {key}"


class TestGetLabel:
    def test_sunrise_label(self):
        assert ZmanimClient.get_label("sunrise") == "זריחה"

    def test_sunset_label(self):
        assert ZmanimClient.get_label("sunset") == "שקיעה"

    def test_chatzot_label(self):
        assert "חצות" in ZmanimClient.get_label("chatzot")

    def test_unknown_key_returns_key_itself(self):
        assert ZmanimClient.get_label("unknownKey") == "unknownKey"

    def test_all_labels_are_hebrew(self):
        for key, label in ZMANIM_LABELS_HE.items():
            # Hebrew characters are in range \u0590–\u05FF
            has_hebrew = any('\u0590' <= ch <= '\u05ff' for ch in label)
            assert has_hebrew, f"Label for '{key}' has no Hebrew: {label}"


class TestZmanimDataIntegrity:
    def test_sample_fixture_has_all_keys(self, sample_zmanim_data):
        """Verify the test fixture is realistic."""
        expected_keys = ["sunrise", "sunset", "chatzot", "minchaGedola"]
        for key in expected_keys:
            assert key in sample_zmanim_data["times"], f"Missing key: {key}"

    def test_time_format_is_consistent(self, sample_zmanim_data):
        """All times in fixture should extract to HH:MM format."""
        for key in sample_zmanim_data["times"]:
            t = ZmanimClient.extract_time(sample_zmanim_data, key)
            if t:
                assert len(t) == 5
                assert t[2] == ":"
