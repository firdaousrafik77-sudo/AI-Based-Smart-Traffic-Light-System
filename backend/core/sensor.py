"""
Layer 4 - Core: Road sensor
Models a single road's sensor — counts vehicles and calculates flow rate.
In a real system this class would read from hardware; here it's simulated.
"""

import time
from dataclasses import dataclass, field


@dataclass
class RoadSensor:
    """Tracks vehicle count and flow rate for one road."""

    name: str
    vehicle_count: int = 0

    # Internal tracking — set automatically after __init__
    _last_update: float    = field(default=0.0, init=False, repr=False)
    _last_flow_time: float = field(default=0.0, init=False, repr=False)
    _last_count: int       = field(default=0,   init=False, repr=False)

    def __post_init__(self):
        now = time.time()
        self._last_update    = now
        self._last_flow_time = now
        self._last_count     = 0

    # ------------------------------------------------------------------ #
    #  Mutators                                                            #
    # ------------------------------------------------------------------ #

    def update(self, count: int):
        """Replace current count with a direct sensor reading."""
        self._last_count     = self.vehicle_count
        self._last_flow_time = self._last_update
        self.vehicle_count   = count
        self._last_update    = time.time()

    def add_vehicles(self, increment: int):
        """Spawn new vehicles arriving at this road."""
        self._last_count     = self.vehicle_count
        self._last_flow_time = self._last_update
        self.vehicle_count  += increment
        self._last_update    = time.time()

    def remove_vehicles(self, count: int):
        """Remove vehicles that passed through the green light."""
        self.vehicle_count = max(0, self.vehicle_count - count)

    # ------------------------------------------------------------------ #
    #  Read                                                                #
    # ------------------------------------------------------------------ #

    def get_flow_rate(self) -> float:
        """
        Vehicles per minute based on how many vehicles entered/left
        since the last call.
        """
        now       = time.time()
        time_diff = now - self._last_flow_time

        if time_diff < 0.1:
            return 0.0

        change = abs(self._last_count - self.vehicle_count)
        rate   = (change / time_diff) * 60   # per minute

        # Update snapshot for next call
        self._last_count     = self.vehicle_count
        self._last_flow_time = now

        return max(0.0, rate)
