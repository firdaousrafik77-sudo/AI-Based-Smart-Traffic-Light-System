"""
Layer 1 - Models: Emergency-related data structures
These are plain data containers — no logic, just structure.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EmergencyType(Enum):
    ACCIDENT    = "accident"
    AMBULANCE   = "ambulance"
    FIRE_TRUCK  = "fire_truck"
    CONGESTION  = "congestion"
    PREDICTIVE  = "predictive"
    TIME_BASED  = "time_based"
    WEATHER     = "weather"


@dataclass
class EmergencyEvent:
    """One emergency event — stores all information about it."""
    type: EmergencyType
    location: str          # road name or "all"
    priority: int          # 1 (low) to 5 (highest)
    timestamp: datetime
    description: str
    duration: int          # how many seconds this event lasts
    active: bool = True


@dataclass
class TrafficHistory:
    """One snapshot of a road's traffic — used for pattern detection."""
    road: str
    timestamp: float       # unix timestamp
    vehicle_count: int
    flow_rate: float       # vehicles per minute
