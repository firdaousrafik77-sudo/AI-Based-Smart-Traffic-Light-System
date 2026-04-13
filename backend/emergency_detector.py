"""Emergency Detection Module for Smart Traffic Control System"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class EmergencyType(Enum):
    ACCIDENT = "accident"
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_truck""""Emergency Detection Module - FIXED for fewer false positives"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class EmergencyType(Enum):
    ACCIDENT = "accident"
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_truck"
    CONGESTION = "congestion"
    PREDICTIVE = "predictive"
    TIME_BASED = "time_based"
    WEATHER = "weather"

@dataclass
class EmergencyEvent:
    """Represents an emergency event"""
    type: EmergencyType
    location: str
    priority: int  # 1-5, 5 being highest
    timestamp: datetime
    description: str
    duration: int  # seconds
    active: bool = True

@dataclass
class TrafficHistory:
    """Tracks traffic history for pattern detection"""
    road: str
    timestamp: float
    vehicle_count: int
    flow_rate: float

class EmergencyDetector:
    """Advanced emergency detection system with multiple detection methods"""

    def __init__(self, config):
        self.config = config
        self.active_emergencies: List[EmergencyEvent] = []
        self.traffic_history: Dict[str, List[TrafficHistory]] = {
            road: [] for road in ["North", "South", "East", "West"]
        }
        self.history_window = 300  # 5 minutes of history
        self.weather_conditions = "clear"
        self.last_weather_change = time.time()
        
        # NEW: Track last accident per road to prevent duplicates
        self.last_accident_time: Dict[str, float] = {
            road: 0 for road in ["North", "South", "East", "West"]
        }
        self.accident_cooldown_seconds = 120  # 2 minutes between accidents on same road
        
        # NEW: Minimum confidence threshold for accidents
        self.accident_confidence_threshold = 0.7
        
        # NEW: Track if time-based emergency is already active
        self.time_based_active = False
        self.time_based_end_time = 0

    def update_traffic_history(self, road: str, vehicle_count: int, flow_rate: float):
        """Update traffic history for pattern detection"""
        history = TrafficHistory(
            road=road,
            timestamp=time.time(),
            vehicle_count=vehicle_count,
            flow_rate=flow_rate
        )

        self.traffic_history[road].append(history)

        # Keep only recent history
        cutoff_time = time.time() - self.history_window
        self.traffic_history[road] = [
            h for h in self.traffic_history[road] if h.timestamp > cutoff_time
        ]

    def detect_accident(self, current_traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        """Detect accidents based on sudden traffic drops or unusual patterns"""
        current_time = time.time()
        
        for road, count in current_traffic.items():
            # CHECK COOLDOWN - Don't detect another accident on same road too soon
            if current_time - self.last_accident_time.get(road, 0) < self.accident_cooldown_seconds:
                continue
                
            history = self.traffic_history[road]

            if len(history) < 10:  # Need more history for accuracy (was 5)
                continue

            # Calculate rolling averages
            recent_counts = [h.vehicle_count for h in history[-5:]]
            recent_avg = sum(recent_counts) / len(recent_counts)
            
            # Calculate longer term average for baseline
            long_term_counts = [h.vehicle_count for h in history[-15:]]
            long_term_avg = sum(long_term_counts) / len(long_term_counts)
            
            # Calculate confidence score
            confidence = 0.0
            
            # Check for sudden drop (possible accident)
            if recent_avg > 20 and count < recent_avg * 0.3:  # 70% drop
                confidence += 0.6
                
            # Check against long-term baseline
            if long_term_avg > 25 and count < long_term_avg * 0.25:  # 75% drop from baseline
                confidence += 0.4
                
            # Check for unusual pattern (normally busy road suddenly empty)
            if long_term_avg > 20 and count < 5:
                confidence += 0.3
                
            # NEW: Verify with neighboring roads - if all roads dropped, it's not an accident
            other_roads = [r for r in current_traffic.keys() if r != road]
            other_avg = sum(current_traffic[r] for r in other_roads) / len(other_roads)
            
            # If other roads also dropped significantly, it might be a simulation quirk, not accident
            if other_avg < long_term_avg * 0.5:
                confidence *= 0.5  # Reduce confidence
                
            # Only trigger if confidence is high enough
            if confidence >= self.accident_confidence_threshold:
                self.last_accident_time[road] = current_time
                return EmergencyEvent(
                    type=EmergencyType.ACCIDENT,
                    location=road,
                    priority=5,
                    timestamp=datetime.now(),
                    description=f"Accident detected on {road} (confidence: {confidence:.0%})",
                    duration=180  # 3 minutes (reduced from 5)
                )

        return None

    def detect_emergency_vehicle(self) -> Optional[EmergencyEvent]:
        """Simulate emergency vehicle detection - REDUCED frequency"""
        # Reduced probability (was 0.0005, now 0.0001 = 0.01% per check)
        if random.random() < 0.0001:
            locations = ["North", "South", "East", "West"]
            location = random.choice(locations)
            vehicle_types = [
                (EmergencyType.AMBULANCE, "🚨 Ambulance approaching"),
                (EmergencyType.FIRE_TRUCK, "🔥 Fire truck approaching")
            ]
            vehicle_type, description = random.choice(vehicle_types)

            return EmergencyEvent(
                type=vehicle_type,
                location=location,
                priority=5,
                timestamp=datetime.now(),
                description=f"{description} from {location} direction",
                duration=45  # 45 seconds (was 60)
            )

        return None

    def detect_time_based_emergency(self) -> Optional[EmergencyEvent]:
        """Detect time-based priority situations - SINGLE ACTIVE AT A TIME"""
        now = datetime.now()
        hour = now.hour
        
        current_time = time.time()
        
        # Check if time-based emergency is already active
        if self.time_based_active and current_time < self.time_based_end_time:
            return None  # Already active, don't create duplicate
            
        # Rush hour priority (7-9 AM, 5-7 PM)
        if (7 <= hour <= 9) or (17 <= hour <= 19):
            self.time_based_active = True
            self.time_based_end_time = current_time + 3600  # 1 hour
            return EmergencyEvent(
                type=EmergencyType.TIME_BASED,
                location="all",
                priority=2,
                timestamp=now,
                description="Rush hour traffic optimization active",
                duration=3600  # 1 hour
            )

        # School zone times (8-9 AM, 2-4 PM on weekdays)
        if now.weekday() < 5:  # Monday-Friday
            if (8 <= hour <= 9) or (14 <= hour <= 16):
                self.time_based_active = True
                self.time_based_end_time = current_time + 3600
                return EmergencyEvent(
                    type=EmergencyType.TIME_BASED,
                    location="all",
                    priority=3,
                    timestamp=now,
                    description="School zone safety mode active",
                    duration=3600
                )
        
        # Reset time-based flag if no longer in time period
        self.time_based_active = False
        return None

    def detect_weather_emergency(self, current_traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        """Simulate weather-based emergency conditions"""
        # Reduced frequency (was 1800, now 3600 seconds = 1 hour)
        if time.time() - self.last_weather_change > 3600:
            if random.random() < 0.05:  # 5% chance (was 10%)
                weather_options = ["clear", "rain", "snow", "fog"]
                old_weather = self.weather_conditions
                self.weather_conditions = random.choice(weather_options)
                self.last_weather_change = time.time()

                if self.weather_conditions != "clear":
                    return EmergencyEvent(
                        type=EmergencyType.WEATHER,
                        location="all",
                        priority=2,
                        timestamp=datetime.now(),
                        description=f"Weather: {self.weather_conditions}",
                        duration=1800  # 30 minutes
                    )

        return None

    def detect_predictive_emergency(self, predictions: Dict) -> Optional[EmergencyEvent]:
        """Use ML predictions to detect upcoming congestion"""
        if not predictions:
            return None

        # Check if any road is predicted to exceed emergency threshold
        for road, predicted_count in predictions.items():
            if predicted_count > self.config.EMERGENCY_SINGLE_ROAD_THRESHOLD * 1.5:
                return EmergencyEvent(
                    type=EmergencyType.PREDICTIVE,
                    location=road,
                    priority=3,
                    timestamp=datetime.now(),
                    description=f"Predicted severe congestion on {road}",
                    duration=180  # 3 minutes
                )

        return None

    def detect_congestion_emergency(self, current_traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        """Enhanced congestion detection - HIGHER thresholds"""
        total_traffic = sum(current_traffic.values())
        max_single_road = max(current_traffic.values())

        # Critical congestion - higher thresholds
        if total_traffic > self.config.EMERGENCY_TRAFFIC_THRESHOLD * 2:  # 200 vehicles (was 150)
            congested_road = max(current_traffic, key=current_traffic.get)
            return EmergencyEvent(
                type=EmergencyType.CONGESTION,
                location=congested_road,
                priority=4,
                timestamp=datetime.now(),
                description=f"Critical congestion: {total_traffic} total vehicles",
                duration=300  # 5 minutes
            )

        # Single road emergency - higher threshold
        if max_single_road > self.config.EMERGENCY_SINGLE_ROAD_THRESHOLD * 1.5:  # 75 vehicles (was 60)
            congested_road = max(current_traffic, key=current_traffic.get)
            return EmergencyEvent(
                type=EmergencyType.CONGESTION,
                location=congested_road,
                priority=3,
                timestamp=datetime.now(),
                description=f"Heavy congestion on {congested_road}",
                duration=180  # 3 minutes
            )

        return None

    def check_all_emergencies(self, current_traffic: Dict[str, int],
                            predictions: Optional[Dict] = None) -> Optional[EmergencyEvent]:
        """Run all emergency detection methods"""
        
        # Update traffic history for pattern detection
        for road, count in current_traffic.items():
            flow_rate = count / 60
            self.update_traffic_history(road, count, flow_rate)

        # Clean up expired emergencies first
        self.cleanup_expired_emergencies()

        # Check each detection method
        detections = [
            self.detect_time_based_emergency(),  # Check time first (lowest priority but longest lasting)
            self.detect_weather_emergency(current_traffic),
            self.detect_congestion_emergency(current_traffic),
            self.detect_predictive_emergency(predictions),
            self.detect_accident(current_traffic),  # Accidents are high priority
            self.detect_emergency_vehicle()  # Emergency vehicles are highest priority
        ]

        # Return the highest priority emergency (sorted by priority)
        valid_emergencies = [e for e in detections if e is not None]
        if valid_emergencies:
            valid_emergencies.sort(key=lambda e: e.priority, reverse=True)
            emergency = valid_emergencies[0]

            # Check if this exact emergency is already active
            for active in self.active_emergencies:
                if (active.type == emergency.type and
                    active.location == emergency.location and
                    active.active):
                    # Update existing instead of creating new
                    active.timestamp = emergency.timestamp
                    active.description = emergency.description
                    return None

            # Add to active emergencies
            self.active_emergencies.append(emergency)
            logger.warning(f"🚨 EMERGENCY DETECTED: {emergency.description}")
            return emergency

        return None

    def get_weather_modifier(self) -> float:
        """Get traffic flow modifier based on weather"""
        modifiers = {
            "clear": 1.0,
            "rain": 0.8,   # 20% slower (was 30%)
            "snow": 0.7,   # 30% slower (was 50%)
            "fog": 0.75    # 25% slower (was 40%)
        }
        return modifiers.get(self.weather_conditions, 1.0)

    def cleanup_expired_emergencies(self):
        """Remove expired emergency events"""
        current_time = datetime.now()
        before_count = len(self.active_emergencies)
        
        self.active_emergencies = [
            e for e in self.active_emergencies
            if e.active and (current_time - e.timestamp).seconds < e.duration
        ]
        
        # Reset time_based flag if it expired
        if self.time_based_active and current_time.timestamp() > self.time_based_end_time:
            self.time_based_active = False

    def get_active_emergencies(self) -> List[EmergencyEvent]:
        """Get list of currently active emergencies"""
        self.cleanup_expired_emergencies()
        return self.active_emergencies

    def get_emergency_log(self, limit: int = 10) -> List[EmergencyEvent]:
        """Get recent emergency events (active and inactive)"""
        all_emergencies = sorted(
            self.active_emergencies,
            key=lambda e: e.timestamp,
            reverse=True
        )
        return all_emergencies[:limit]
    CONGESTION = "congestion"
    PREDICTIVE = "predictive"
    TIME_BASED = "time_based"
    WEATHER = "weather"

@dataclass
class EmergencyEvent:
    """Represents an emergency event"""
    type: EmergencyType
    location: str
    priority: int  # 1-5, 5 being highest
    timestamp: datetime
    description: str
    duration: int  # seconds
    active: bool = True

@dataclass
class TrafficHistory:
    """Tracks traffic history for pattern detection"""
    road: str
    timestamp: float
    vehicle_count: int
    flow_rate: float

class EmergencyDetector:
    """Advanced emergency detection system with multiple detection methods"""

    def __init__(self, config):
        self.config = config
        self.active_emergencies: List[EmergencyEvent] = []
        self.traffic_history: Dict[str, List[TrafficHistory]] = {
            road: [] for road in ["North", "South", "East", "West"]
        }
        self.history_window = 300  # 5 minutes of history
        self.weather_conditions = "clear"  # "clear", "rain", "snow", "fog"
        self.last_weather_change = time.time()

    def update_traffic_history(self, road: str, vehicle_count: int, flow_rate: float):
        """Update traffic history for pattern detection"""
        history = TrafficHistory(
            road=road,
            timestamp=time.time(),
            vehicle_count=vehicle_count,
            flow_rate=flow_rate
        )

        self.traffic_history[road].append(history)

        # Keep only recent history
        cutoff_time = time.time() - self.history_window
        self.traffic_history[road] = [
            h for h in self.traffic_history[road] if h.timestamp > cutoff_time
        ]

    def detect_accident(self, current_traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        """Detect accidents based on sudden traffic drops or unusual patterns"""
        for road, count in current_traffic.items():
            history = self.traffic_history[road]

            if len(history) < 5:  # Need some history
                continue

            # Check for sudden traffic drop (possible accident blocking road)
            recent_avg = sum(h.vehicle_count for h in history[-5:]) / 5
            if recent_avg > 15 and count < recent_avg * 0.3:  # 70% drop
                return EmergencyEvent(
                    type=EmergencyType.ACCIDENT,
                    location=road,
                    priority=5,
                    timestamp=datetime.now(),
                    description=f"Sudden traffic drop on {road}: {recent_avg:.1f} → {count} vehicles",
                    duration=300  # 5 minutes
                )

            # Check for unusual traffic pattern (normally busy road suddenly empty)
            if len(history) >= 10:
                long_avg = sum(h.vehicle_count for h in history[-10:]) / 10
                if long_avg > 20 and count < 5:  # Normally busy, now almost empty
                    return EmergencyEvent(
                        type=EmergencyType.ACCIDENT,
                        location=road,
                        priority=4,
                        timestamp=datetime.now(),
                        description=f"Unusual traffic pattern on {road}: normally {long_avg:.1f}, now {count}",
                        duration=240  # 4 minutes
                    )

        return None

    def detect_emergency_vehicle(self) -> Optional[EmergencyEvent]:
        """Simulate emergency vehicle detection"""
        # Random emergency vehicle detection (rare but realistic)
        if random.random() < 0.0005:  # 0.05% chance per check
            locations = ["North", "South", "East", "West"]
            location = random.choice(locations)
            vehicle_types = [
                (EmergencyType.AMBULANCE, "🚨 Ambulance approaching"),
                (EmergencyType.FIRE_TRUCK, "🔥 Fire truck approaching")
            ]
            vehicle_type, description = random.choice(vehicle_types)

            return EmergencyEvent(
                type=vehicle_type,
                location=location,
                priority=5,
                timestamp=datetime.now(),
                description=f"{description} from {location} direction",
                duration=60  # 1 minute priority
            )

        return None

    def detect_time_based_emergency(self) -> Optional[EmergencyEvent]:
        """Detect time-based priority situations"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute

        # Rush hour priority (7-9 AM, 5-7 PM)
        if (7 <= hour <= 9) or (17 <= hour <= 19):
            return EmergencyEvent(
                type=EmergencyType.TIME_BASED,
                location="all",
                priority=2,
                timestamp=now,
                description="Rush hour traffic optimization active",
                duration=3600  # 1 hour
            )

        # School zone times (8-9 AM, 2-4 PM on weekdays)
        if now.weekday() < 5:  # Monday-Friday
            if (8 <= hour <= 9) or (14 <= hour <= 16):
                return EmergencyEvent(
                    type=EmergencyType.TIME_BASED,
                    location="all",
                    priority=3,
                    timestamp=now,
                    description="School zone safety mode active",
                    duration=3600  # 1 hour
                )

        return None

    def detect_weather_emergency(self, current_traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        """Simulate weather-based emergency conditions"""
        # Random weather changes
        if time.time() - self.last_weather_change > 1800:  # Check every 30 minutes
            if random.random() < 0.1:  # 10% chance of weather change
                weather_options = ["clear", "rain", "snow", "fog"]
                old_weather = self.weather_conditions
                self.weather_conditions = random.choice(weather_options)
                self.last_weather_change = time.time()

                if self.weather_conditions != "clear":
                    return EmergencyEvent(
                        type=EmergencyType.WEATHER,
                        location="all",
                        priority=2,
                        timestamp=datetime.now(),
                        description=f"Weather condition changed: {old_weather} → {self.weather_conditions}",
                        duration=1800  # 30 minutes
                    )

        return None

    def detect_predictive_emergency(self, predictions: Dict) -> Optional[EmergencyEvent]:
        """Use ML predictions to detect upcoming congestion"""
        if not predictions:
            return None

        # Check if any road is predicted to exceed emergency threshold in next 5 minutes
        for road, predicted_count in predictions.items():
            if predicted_count > self.config.EMERGENCY_SINGLE_ROAD_THRESHOLD:
                return EmergencyEvent(
                    type=EmergencyType.PREDICTIVE,
                    location=road,
                    priority=3,
                    timestamp=datetime.now(),
                    description=f"Predicted congestion on {road}: {predicted_count} vehicles expected",
                    duration=300  # 5 minutes
                )

        return None

    def detect_congestion_emergency(self, current_traffic: Dict[str, int]) -> Optional[EmergencyEvent]:
        """Enhanced congestion detection beyond basic thresholds"""
        total_traffic = sum(current_traffic.values())
        max_single_road = max(current_traffic.values())

        # Critical congestion
        if total_traffic > self.config.EMERGENCY_TRAFFIC_THRESHOLD * 1.5:  # 150 vehicles
            congested_road = max(current_traffic, key=current_traffic.get)
            return EmergencyEvent(
                type=EmergencyType.CONGESTION,
                location=congested_road,
                priority=4,
                timestamp=datetime.now(),
                description=f"Critical congestion: {total_traffic} total vehicles",
                duration=600  # 10 minutes
            )

        # Single road emergency
        if max_single_road > self.config.EMERGENCY_SINGLE_ROAD_THRESHOLD * 1.2:  # 60 vehicles
            congested_road = max(current_traffic, key=current_traffic.get)
            return EmergencyEvent(
                type=EmergencyType.CONGESTION,
                location=congested_road,
                priority=3,
                timestamp=datetime.now(),
                description=f"Heavy congestion on {congested_road}: {max_single_road} vehicles",
                duration=300  # 5 minutes
            )

        return None

    def check_all_emergencies(self, current_traffic: Dict[str, int],
                            predictions: Optional[Dict] = None) -> Optional[EmergencyEvent]:
        """Run all emergency detection methods"""

        # Update traffic history for pattern detection
        for road, count in current_traffic.items():
            flow_rate = count / 60  # vehicles per minute (simplified)
            self.update_traffic_history(road, count, flow_rate)

        # Check each detection method
        detections = [
            self.detect_accident(current_traffic),
            self.detect_emergency_vehicle(),
            self.detect_time_based_emergency(),
            self.detect_weather_emergency(current_traffic),
            self.detect_predictive_emergency(predictions),
            self.detect_congestion_emergency(current_traffic)
        ]

        # Return the highest priority emergency
        valid_emergencies = [e for e in detections if e is not None]
        if valid_emergencies:
            # Sort by priority (highest first) and return the most critical
            valid_emergencies.sort(key=lambda e: e.priority, reverse=True)
            emergency = valid_emergencies[0]

            # Check if this emergency is already active
            for active in self.active_emergencies:
                if (active.type == emergency.type and
                    active.location == emergency.location and
                    active.active):
                    return None  # Already handling this emergency

            # Add to active emergencies
            self.active_emergencies.append(emergency)
            logger.warning(f"🚨 EMERGENCY DETECTED: {emergency.description}")
            return emergency

        return None

    def get_weather_modifier(self) -> float:
        """Get traffic flow modifier based on weather"""
        modifiers = {
            "clear": 1.0,
            "rain": 0.7,   # 30% slower clearing
            "snow": 0.5,   # 50% slower clearing
            "fog": 0.6     # 40% slower clearing
        }
        return modifiers.get(self.weather_conditions, 1.0)

    def cleanup_expired_emergencies(self):
        """Remove expired emergency events"""
        current_time = datetime.now()
        self.active_emergencies = [
            e for e in self.active_emergencies
            if e.active and (current_time - e.timestamp).seconds < e.duration
        ]

    def get_active_emergencies(self) -> List[EmergencyEvent]:
        """Get list of currently active emergencies"""
        return [e for e in self.active_emergencies if e.active]

    def get_emergency_log(self, limit: int = 10) -> List[EmergencyEvent]:
        """Get recent emergency events (active and inactive)"""
        all_emergencies = sorted(
            self.active_emergencies,
            key=lambda e: e.timestamp,
            reverse=True
        )
        return all_emergencies[:limit]