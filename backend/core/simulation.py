"""
Layer 4 - Core: Simulation manager
Owns the three background tasks that keep the simulation alive:
  1. _spawn_vehicles  — adds cars to roads over time
  2. intersection.control_cycle — switches lights (runs inside intersection)
  3. _emergency_handler — triggers random emergency events

Start/stop is called by the API layer.
"""

import asyncio
import random
import logging
from datetime import datetime

from ..models.traffic import TrafficLightState

logger = logging.getLogger(__name__)


class SimulationManager:
    """
    Manages the lifecycle of the traffic simulation.
    Call start() to begin and stop() to end cleanly.
    """

    def __init__(self, intersection, db, config):
        self.intersection = intersection
        self.db           = db
        self.config       = config

        self.running = False

        self._spawn_task     = None
        self._control_task   = None
        self._emergency_task = None

    # ------------------------------------------------------------------ #
    #  Public interface                                                    #
    # ------------------------------------------------------------------ #

    async def start(self) -> bool:
        """Start all background tasks. Returns False if already running."""
        if self.running:
            return False

        self.running = True

        # Give each road a realistic starting vehicle count
        for road in self.intersection.ROADS:
            self.intersection.sensors[road].vehicle_count = random.randint(5, 15)
            logger.info(f"Initialised {road}: "
                        f"{self.intersection.sensors[road].vehicle_count} vehicles")

        self._spawn_task     = asyncio.create_task(self._spawn_vehicles())
        self._control_task   = asyncio.create_task(self.intersection.control_cycle())
        self._emergency_task = asyncio.create_task(self._emergency_handler())

        logger.info("Simulation started — all tasks active")
        return True

    async def stop(self) -> bool:
        """Cancel all tasks and reset intersection to idle state."""
        self.running = False

        for task in (self._spawn_task, self._control_task, self._emergency_task):
            if task and not task.done():
                task.cancel()

        self._spawn_task = self._control_task = self._emergency_task = None

        self._reset_intersection()
        logger.info("Simulation stopped")
        return True

    # ------------------------------------------------------------------ #
    #  Background tasks                                                    #
    # ------------------------------------------------------------------ #

    async def _spawn_vehicles(self):
        """Add vehicles to each road at a rate that changes by time of day."""
        logger.info("Vehicle spawner started")
        try:
            while self.running:
                try:
                    hour = datetime.now().hour

                    if 7 <= hour <= 9 or 17 <= hour <= 19:
                        spawn_rate  = self.config.SPAWN_RATE_RUSH_HOUR
                        rush_factor = 1.5
                    elif 23 <= hour or hour <= 5:
                        spawn_rate  = self.config.SPAWN_RATE_NIGHT
                        rush_factor = 0.5
                    else:
                        spawn_rate  = self.config.SPAWN_RATE_NORMAL
                        rush_factor = 1.0

                    await asyncio.sleep(spawn_rate)

                    if not self.running:
                        break

                    for road in self.intersection.ROADS:
                        # All roads scale with rush_factor — no directional bias.
                        # NS roads get a small natural advantage (city layout),
                        # but EW also sees increased load during rush hours.
                        if rush_factor > 1:
                            base = random.randint(2, 5)
                            ns_bonus = 1 if road in ('North', 'South') else 0
                            increment = base + ns_bonus   # NS: 3-6, EW: 2-5
                        elif rush_factor < 1:
                            increment = random.randint(0, 2)
                        else:
                            increment = random.randint(1, 4)

                        self.intersection.sensors[road].add_vehicles(increment)
                        logger.debug(f"Spawned {increment} on {road} "
                                     f"(total: {self.intersection.sensors[road].vehicle_count})")

                    # Occasionally persist a snapshot — offloaded to a thread
                    # so the synchronous SQLite write never blocks the async loop.
                    if random.random() < 0.1:
                        snapshot = {r: s.vehicle_count
                                    for r, s in self.intersection.sensors.items()}
                        green    = self.intersection.current_green
                        asyncio.create_task(
                            asyncio.to_thread(self.db.save_traffic_data, snapshot, green)
                        )

                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.error(f"Vehicle spawner error: {exc}")
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("Vehicle spawner cancelled")

    async def _emergency_handler(self):
        """
        Randomly fire auto-emergency events while the simulation runs.

        Bug fix (race condition): no longer directly mutates intersection state.
        Instead it pushes an event into intersection.pending_emergency which
        control_cycle() reads at its next safe await point.
        """
        logger.info("Emergency handler started")
        try:
            while self.running:
                try:
                    if random.random() < self.config.EMERGENCY_PROBABILITY:
                        etype    = random.choice(["accident", "ambulance", "fire_truck"])
                        location = random.choice(self.intersection.ROADS)
                        logger.warning(f"AUTO EMERGENCY: {etype} on {location}")

                        # Persist to DB (offloaded so it doesn't block)
                        asyncio.create_task(
                            asyncio.to_thread(
                                self.db.save_emergency_event, etype, location, 3
                            )
                        )

                        # Signal the intersection — control_cycle picks this up
                        # at its next iteration instead of us mutating state directly.
                        self.intersection.pending_emergency = {
                            "type":     etype,
                            "location": location,
                            "axis":     'NS' if location in ('North', 'South') else 'EW',
                        }

                    if self.intersection.emergency_detector:
                        self.intersection.emergency_detector.cleanup_expired()

                    await asyncio.sleep(30)

                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.error(f"Emergency handler error: {exc}")
                    await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info("Emergency handler cancelled")

    # ------------------------------------------------------------------ #
    #  Reset helper                                                        #
    # ------------------------------------------------------------------ #

    def _reset_intersection(self):
        """Put the intersection back to a clean idle state."""
        self.intersection.current_green = None
        self.intersection.state         = TrafficLightState.RED

        for road in self.intersection.ROADS:
            self.intersection.road_light_states[road] = TrafficLightState.RED
            self.intersection.sensors[road].vehicle_count = 0
            self.intersection.wait_times[road]            = 0

        self.intersection.metrics = {
            'total_throughput':      0,
            'average_wait_time':     0,
            'congestion_events':     0,
            'emergency_activations': 0,
        }
