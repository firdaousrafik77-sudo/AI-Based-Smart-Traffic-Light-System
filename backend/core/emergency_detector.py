"""
Layer 4 - Core: Emergency detector
Monitors traffic data and flags emergency situations.

Detection methods (in priority order):
  5 - Emergency vehicle (ambulance / fire truck)
  5 - Accident (sudden traffic drop on one road)
  4 - Critical congestion (too many vehicles total)
  3 - Heavy congestion on single road
  3 - Predictive congestion (ML says it's coming)
  2 - Rush hour / school zone (time-based)
  2 - Weather change
"""

import random
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..models.emergency import EmergencyType, EmergencyEvent, TrafficHistory

logger = logging.getLogger(__name__)


class EmergencyDetector:
    """
    Runs several checks every decision cycle and returns the
    highest-priority emergency it finds (or None if everything is fine).
    """

    ROADS = ["North", "South", "East", "West"]

    def __init__(self, config):
        self.config = config

        self.active_emergencies: List[EmergencyEvent] = []
        self.traffic_history: Dict[str, List[TrafficHistory]] = {
            road: [] for road in self.ROADS
        }
        self.history_window = 300          # keep 5 minutes of history

        # Weather simulation
        self.weather_conditions  = "clear"
        self.last_weather_change = time.time()

        # Accident detection — prevent duplicate alerts on the same road
        self.last_accident_time: Dict[str, float] = {r: 0 for r in self.ROADS}
        self.accident_cooldown      = 120           # seconds between alerts per road
        self.accident_confidence_th = 0.7           # minimum confidence to report

        # Time-based emergency — only one active at a time
        self._time_based_active   = False
        self._time_based_end_time = 0.0

    # ------------------------------------------------------------------ #
    #  Traffic history                                                     #
    # ------------------------------------------------------------------ #

    def _update_history(self, road: str, vehicle_count: int, flow_rate: float):
        entry = TrafficHistory(
            road=road,
            timestamp=time.time(),
            vehicle_count=vehicle_count,
            flow_rate=flow_rate,
        )
        self.traffic_history[road].append(entry)
        cutoff = time.time() - self.history_window
        self.traffic_history[road] = [
            h for h in self.traffic_history[road] if h.timestamp > cutoff
        ]

    # ------------------------------------------------------------------ #
    #  Individual detection methods                                        #
    # ------------------------------------------------------------------ #

    def _detect_accident(self, traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        now = time.time()
        for road, count in traffic.items():
            if now - self.last_accident_time[road] < self.accident_cooldown:
                continue

            history = self.traffic_history[road]
            if len(history) < 10:
                continue

            recent_avg    = sum(h.vehicle_count for h in history[-5:])  / 5
            long_term_avg = sum(h.vehicle_count for h in history[-15:]) / 15

            confidence = 0.0
            if recent_avg > 20 and count < recent_avg * 0.3:
                confidence += 0.6
            if long_term_avg > 25 and count < long_term_avg * 0.25:
                confidence += 0.4
            if long_term_avg > 20 and count < 5:
                confidence += 0.3

            # If all roads dropped it might be a simulation reset, not an accident
            other_avg = sum(traffic[r] for r in self.ROADS if r != road) / 3
            if other_avg < long_term_avg * 0.5:
                confidence *= 0.5

            if confidence >= self.accident_confidence_th:
                self.last_accident_time[road] = now
                return EmergencyEvent(
                    type=EmergencyType.ACCIDENT,
                    location=road,
                    priority=5,
                    timestamp=datetime.now(),
                    description=f"Accident on {road} (confidence {confidence:.0%})",
                    duration=180,
                )
        return None

    def _detect_emergency_vehicle(self) -> Optional[EmergencyEvent]:
        """Rare random emergency vehicle — 0.01% chance per check."""
        if random.random() >= 0.0001:
            return None
        location    = random.choice(self.ROADS)
        vtype, desc = random.choice([
            (EmergencyType.AMBULANCE,  "Ambulance approaching"),
            (EmergencyType.FIRE_TRUCK, "Fire truck approaching"),
        ])
        return EmergencyEvent(
            type=vtype,
            location=location,
            priority=5,
            timestamp=datetime.now(),
            description=f"{desc} from {location}",
            duration=45,
        )

    def _detect_congestion(self, traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        total    = sum(traffic.values())
        max_road = max(traffic.values())
        busiest  = max(traffic, key=traffic.get)

        if total > self.config.EMERGENCY_TRAFFIC_THRESHOLD * 2:
            return EmergencyEvent(
                type=EmergencyType.CONGESTION, location=busiest,
                priority=4, timestamp=datetime.now(),
                description=f"Critical congestion: {total} vehicles total",
                duration=300,
            )
        if max_road > self.config.EMERGENCY_SINGLE_ROAD_THRESHOLD * 1.5:
            return EmergencyEvent(
                type=EmergencyType.CONGESTION, location=busiest,
                priority=3, timestamp=datetime.now(),
                description=f"Heavy congestion on {busiest}: {max_road} vehicles",
                duration=180,
            )
        return None

    def _detect_predictive(self, predictions: Optional[Dict]) -> Optional[EmergencyEvent]:
        if not predictions:
            return None
        threshold = self.config.EMERGENCY_SINGLE_ROAD_THRESHOLD * 1.5
        for road, predicted in predictions.items():
            if isinstance(predicted, int) and predicted > threshold:
                return EmergencyEvent(
                    type=EmergencyType.PREDICTIVE, location=road,
                    priority=3, timestamp=datetime.now(),
                    description=f"Predicted severe congestion on {road}",
                    duration=180,
                )
        return None

    def _detect_time_based(self) -> Optional[EmergencyEvent]:
        now  = datetime.now()
        hour = now.hour
        cur  = time.time()

        if self._time_based_active and cur < self._time_based_end_time:
            return None   # already active

        if (7 <= hour <= 9) or (17 <= hour <= 19):
            self._time_based_active   = True
            self._time_based_end_time = cur + 3600
            return EmergencyEvent(
                type=EmergencyType.TIME_BASED, location="all",
                priority=2, timestamp=now,
                description="Rush hour optimisation active",
                duration=3600,
            )
        if now.weekday() < 5 and ((8 <= hour <= 9) or (14 <= hour <= 16)):
            self._time_based_active   = True
            self._time_based_end_time = cur + 3600
            return EmergencyEvent(
                type=EmergencyType.TIME_BASED, location="all",
                priority=3, timestamp=now,
                description="School zone safety mode active",
                duration=3600,
            )
        self._time_based_active = False
        return None

    def _detect_weather(self, _traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        if time.time() - self.last_weather_change < 3600:
            return None
        if random.random() >= 0.05:
            return None
        options = ["clear", "rain", "snow", "fog"]
        self.weather_conditions  = random.choice(options)
        self.last_weather_change = time.time()
        if self.weather_conditions == "clear":
            return None
        return EmergencyEvent(
            type=EmergencyType.WEATHER, location="all",
            priority=2, timestamp=datetime.now(),
            description=f"Weather: {self.weather_conditions}",
            duration=1800,
        )

    # ------------------------------------------------------------------ #
    #  Public interface                                                    #
    # ------------------------------------------------------------------ #

    def check_all_emergencies(self, traffic: Dict[str, int],
                              predictions: Optional[Dict] = None
                              ) -> Optional[EmergencyEvent]:
        """
        Run all detectors, return the highest-priority new emergency.
        Returns None if nothing new is happening.
        """
        for road, count in traffic.items():
            # Flow rate = vehicles that moved since last snapshot / elapsed time.
            # We approximate it from the delta between current and last recorded count.
            history    = self.traffic_history[road]
            last_count = history[-1].vehicle_count if history else count
            elapsed    = time.time() - (history[-1].timestamp if history else time.time())
            flow_rate  = abs(count - last_count) / elapsed * 60 if elapsed > 0.1 else 0.0
            self._update_history(road, count, flow_rate)

        self.cleanup_expired()

        candidates = [
            self._detect_emergency_vehicle(),
            self._detect_accident(traffic),
            self._detect_congestion(traffic),
            self._detect_predictive(predictions),
            self._detect_time_based(),
            self._detect_weather(traffic),
        ]
        candidates = [e for e in candidates if e is not None]
        if not candidates:
            return None

        candidates.sort(key=lambda e: e.priority, reverse=True)
        best = candidates[0]

        # Don't duplicate an already-active emergency of the same type+location
        for active in self.active_emergencies:
            if active.type == best.type and active.location == best.location:
                active.timestamp   = best.timestamp
                active.description = best.description
                return None

        self.active_emergencies.append(best)
        logger.warning(f"EMERGENCY: {best.description}")
        return best

    def get_active_emergencies(self) -> List[EmergencyEvent]:
        self.cleanup_expired()
        return list(self.active_emergencies)

    def get_emergency_log(self, limit: int = 10) -> List[EmergencyEvent]:
        return sorted(self.active_emergencies,
                      key=lambda e: e.timestamp, reverse=True)[:limit]

    def cleanup_expired(self):
        """Remove emergencies whose duration has passed."""
        now = datetime.now()
        self.active_emergencies = [
            e for e in self.active_emergencies
            if e.active and (now - e.timestamp).total_seconds() < e.duration
        ]
        if self._time_based_active and time.time() > self._time_based_end_time:
            self._time_based_active = False

    # ------------------------------------------------------------------ #
    #  Helpers used by TrafficIntersection                                 #
    # ------------------------------------------------------------------ #

    def get_weather_modifier(self) -> float:
        """How much to slow down green-phase vehicle flow in bad weather."""
        return {"clear": 1.0, "rain": 0.8, "snow": 0.7, "fog": 0.75}.get(
            self.weather_conditions, 1.0
        )
