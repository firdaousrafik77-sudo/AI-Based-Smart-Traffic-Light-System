"""
Layer 1 - Models: Traffic light state
Simple enum that represents what colour a light can be.
"""

from enum import Enum


class TrafficLightState(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
