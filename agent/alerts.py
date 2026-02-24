"""Weather anomaly detection — triggers alerts for significant changes."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

log = logging.getLogger(__name__)

WIND_THRESHOLD_KMH = 30
FOG_VISIBILITY_THRESHOLD_M = 1000  # metres
TEMP_CHANGE_THRESHOLD_C = 5        # degrees Celsius


class AlertDetector:
    def detect(
        self,
        current_weather: Dict[str, Any],
        previous_state: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Compare current forecast to saved state.
        Returns a list of anomaly dicts; empty list = no alerts needed.
        """
        anomalies: List[Dict[str, Any]] = []

        # --- extract current hour metrics ---
        hourly = current_weather.get("hourly", {})
        times = hourly.get("time", [])
        now_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        idx = times.index(now_str) if now_str in times else 0

        def get(key):
            values = hourly.get(key, [])
            return values[idx] if idx < len(values) else None

        current_wind = get("wind_speed_10m")
        current_visibility = get("visibility")
        current_temp = get("temperature_2m")

        # --- High wind ---
        if current_wind is not None and current_wind > WIND_THRESHOLD_KMH:
            anomalies.append({
                "type": "wind",
                "current": current_wind,
                "threshold": WIND_THRESHOLD_KMH,
                "emoji": "💨",
                "message": f'רוחות חזקות: {current_wind:.0f} קמ"ש (סף: {WIND_THRESHOLD_KMH})',
            })
            log.info("Anomaly: high wind %.0f km/h", current_wind)

        # --- Heavy fog ---
        if current_visibility is not None and current_visibility < FOG_VISIBILITY_THRESHOLD_M:
            anomalies.append({
                "type": "fog",
                "current": current_visibility,
                "threshold": FOG_VISIBILITY_THRESHOLD_M,
                "emoji": "🌫️",
                "message": f"אובך כבד: ראות {current_visibility:.0f} מטר",
            })
            log.info("Anomaly: fog visibility %.0f m", current_visibility)

        # --- Temperature change vs previous snapshot ---
        if previous_state:
            prev_temp = previous_state.get("snapshot", {}).get("temperature")
            if prev_temp is not None and current_temp is not None:
                diff = current_temp - prev_temp
                if abs(diff) > TEMP_CHANGE_THRESHOLD_C:
                    direction = "עלייה" if diff > 0 else "ירידה"
                    anomalies.append({
                        "type": "temperature",
                        "current": current_temp,
                        "previous": prev_temp,
                        "diff": diff,
                        "emoji": "🌡️",
                        "message": (
                            f"{direction} חדה בטמפרטורה: "
                            f"{prev_temp:.0f}°C → {current_temp:.0f}°C "
                            f"({abs(diff):.1f}° שינוי)"
                        ),
                    })
                    log.info(
                        "Anomaly: temp change %.1f°C (%.0f → %.0f)",
                        diff, prev_temp, current_temp,
                    )

        return anomalies
