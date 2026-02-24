"""State persistence for weather change detection."""
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

log = logging.getLogger(__name__)

STATE_FILE = "state.json"


class StateManager:
    def load(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(STATE_FILE):
            log.info("No previous state found (first run).")
            return None
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            log.info("State loaded from %s (saved at %s)", STATE_FILE, state.get("timestamp"))
            return state
        except Exception as e:
            log.warning("Failed to load state: %s", e)
            return None

    def save(self, weather_data: Dict[str, Any]) -> None:
        snapshot = self._extract_snapshot(weather_data)
        state = {
            "timestamp": datetime.now().isoformat(),
            "snapshot": snapshot,
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            log.info("State saved to %s", STATE_FILE)
        except Exception as e:
            log.warning("Failed to save state: %s", e)

    def _extract_snapshot(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the current hour's key metrics from the forecast."""
        hourly = weather_data.get("hourly", {})
        times = hourly.get("time", [])
        now_str = datetime.now().strftime("%Y-%m-%dT%H:00")

        idx = 0
        if now_str in times:
            idx = times.index(now_str)

        def get(key):
            values = hourly.get(key, [])
            return values[idx] if idx < len(values) else None

        return {
            "time": times[idx] if idx < len(times) else now_str,
            "temperature": get("temperature_2m"),
            "wind_speed": get("wind_speed_10m"),
            "visibility": get("visibility"),
            "precipitation_probability": get("precipitation_probability"),
            "weather_code": get("weather_code"),
        }
