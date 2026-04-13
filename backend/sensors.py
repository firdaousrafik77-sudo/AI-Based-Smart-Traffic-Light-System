"""Placeholder sensors module for the backend."""

from typing import Dict

class DummySensor:
    """A minimal placeholder sensor."""
    def __init__(self, name: str):
        self.name = name
        self.vehicle_count = 0
        self.last_update = 0

    def update(self, count: int):
        self.vehicle_count = count
        self.last_update += 1

    def get_flow_rate(self) -> float:
        return float(self.vehicle_count)
