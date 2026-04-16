"""
Layer 4 - Core: Traffic intersection controller
The main brain of the system.  Manages the four roads, runs the
green/yellow/red cycle, and uses ML + RL + GA to make smart decisions.
"""

import asyncio
import time
import random
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from ..models.traffic import TrafficLightState
from .sensor import RoadSensor
from .. import config as cfg

logger = logging.getLogger(__name__)


class TrafficIntersection:
    """
    Controls one 4-way intersection.

    Two axes share the green light in turns:
        NS axis → North + South roads are GREEN, East + West are RED
        EW axis → East  + West  roads are GREEN, North + South are RED

    The smart_decision() method picks which axis should be green next,
    using (in order of priority):
        1. Emergency detector
        2. RL Q-Learning
        3. ML traffic predictions
        4. Simple traffic-volume comparison (fallback)
    """

    ROADS = ["North", "South", "East", "West"]
    AXES  = {"NS": ["North", "South"], "EW": ["East", "West"]}

    def __init__(self, name: str,
                 ml_predictor=None,
                 rl_optimizer=None,
                 ga_optimizer=None,
                 emergency_detector=None):

        self.name = name

        # One sensor per road
        self.sensors: Dict[str, RoadSensor] = {
            road: RoadSensor(road) for road in self.ROADS
        }

        # Light state
        self.current_green: Optional[str]    = None
        self.state: TrafficLightState        = TrafficLightState.RED
        self.road_light_states: Dict[str, TrafficLightState] = {
            road: TrafficLightState.RED for road in self.ROADS
        }

        # Wait times and skip counters
        self.wait_times:   Dict[str, int] = {road: 0 for road in self.ROADS}
        self.skip_counter: Dict[str, int] = {axis: 0 for axis in self.AXES}

        # Short history for GA
        self.history: deque = deque(maxlen=100)

        # AI components (injected — may be None)
        self.ml_predictor      = ml_predictor
        self.rl_optimizer      = rl_optimizer
        self.ga_optimizer      = ga_optimizer
        self.emergency_detector = emergency_detector
        self.ga_population     = None

        # RL book-keeping
        self.last_state:  Optional[str] = None
        self.last_action: Optional[str] = None

        # Prevent switching too fast
        self.last_switch_time  = 0.0
        self.min_cycle_duration = cfg.MIN_GREEN_DURATION

        # Emergency signal written by SimulationManager, read by control_cycle.
        # Using a dict instead of direct state mutation avoids the race condition.
        self.pending_emergency: dict = {}

        # Performance counters
        self.metrics = {
            'total_throughput':       0,
            'average_wait_time':      0,
            'congestion_events':      0,
            'emergency_activations':  0,
        }

        self._init_ns_green()

    # ------------------------------------------------------------------ #
    #  Initialisation                                                      #
    # ------------------------------------------------------------------ #

    def _init_ns_green(self):
        """Start with North-South green so the system is never in limbo."""
        self.current_green = 'NS'
        self.state = TrafficLightState.GREEN
        for road in self.AXES['NS']:
            self.road_light_states[road] = TrafficLightState.GREEN
        for road in self.AXES['EW']:
            self.road_light_states[road] = TrafficLightState.RED
        logger.info("Initial state: NS=GREEN, EW=RED")

    # ------------------------------------------------------------------ #
    #  Sensor updates                                                      #
    # ------------------------------------------------------------------ #

    async def update_sensors(self, traffic_data: Dict[str, int]):
        for road, count in traffic_data.items():
            if road in self.sensors:
                self.sensors[road].update(count)

    def get_traffic_flow(self) -> Dict[str, float]:
        return {road: sensor.get_flow_rate()
                for road, sensor in self.sensors.items()}

    # ------------------------------------------------------------------ #
    #  Decision making                                                     #
    # ------------------------------------------------------------------ #

    async def smart_decision(self) -> str:
        """
        Decide which axis gets the green light next.
        Returns 'NS' or 'EW'.
        """
        # Don't switch while yellow is still showing
        if self.state == TrafficLightState.YELLOW:
            return self.current_green or 'NS'

        # Respect minimum cycle duration
        if time.time() - self.last_switch_time < self.min_cycle_duration:
            return self.current_green or 'NS'

        now      = datetime.now()
        volumes  = {road: self.sensors[road].vehicle_count for road in self.ROADS}
        predictions = None

        # -- ML predictions --
        if self.ml_predictor:
            try:
                predictions = await self.ml_predictor.predict_traffic(
                    volumes, now.hour, now.weekday()
                )
            except Exception as exc:
                logger.warning(f"ML prediction error: {exc}")

        # -- Emergency detection (highest priority) --
        if self.emergency_detector:
            emergency = self.emergency_detector.check_all_emergencies(
                volumes, predictions
            )
            if emergency:
                self.metrics['emergency_activations'] += 1
                etype = emergency.type.value
                if etype in ('ambulance', 'fire_truck'):
                    axis = 'NS' if emergency.location in ('North', 'South') else 'EW'
                    logger.warning(f"EMERGENCY VEHICLE → {axis} green")
                    return axis
                elif etype == 'accident':
                    # Route traffic away from the accident
                    blocked = 'NS' if emergency.location in ('North', 'South') else 'EW'
                    return 'EW' if blocked == 'NS' else 'NS'
                elif etype in ('congestion', 'predictive'):
                    axis = 'NS' if emergency.location in ('North', 'South') else 'EW'
                    return axis

        # -- RL decision --
        if self.rl_optimizer:
            state  = self.rl_optimizer.get_state(volumes, self.skip_counter)
            action = self.rl_optimizer.choose_action(state)
            self.last_state  = state
            self.last_action = action

            if action in ('NS', 'EW'):
                return action
            elif action == 'emergency':
                busiest = max(volumes, key=volumes.get)
                return 'NS' if busiest in ('North', 'South') else 'EW'
            # 'adaptive_cycle' falls through to ML/fallback below

        # -- ML-weighted decision --
        ns_vol = volumes['North'] + volumes['South']
        ew_vol = volumes['East']  + volumes['West']

        if predictions:
            ns_pred = predictions['North'] + predictions['South']
            ew_pred = predictions['East']  + predictions['West']
            ns_score = ns_vol * 0.6 + ns_pred * 0.4
            ew_score = ew_vol * 0.6 + ew_pred * 0.4
        else:
            ns_score, ew_score = ns_vol, ew_vol

        # -- Skip-counter guard (prevent starvation) --
        for axis in self.AXES:
            if axis != self.current_green:
                self.skip_counter[axis] += 1
            else:
                self.skip_counter[axis] = 0

        if self.skip_counter['NS'] >= 4:
            return 'NS'
        if self.skip_counter['EW'] >= 4:
            return 'EW'

        # -- Simple volume comparison (fallback) --
        if self.current_green == 'NS' and ew_score > ns_score * 1.2:
            return 'EW'
        if self.current_green == 'EW' and ns_score > ew_score * 1.2:
            return 'NS'

        return self.current_green or ('NS' if ns_score >= ew_score else 'EW')

    # ------------------------------------------------------------------ #
    #  Control cycle (runs as a background task)                          #
    # ------------------------------------------------------------------ #

    async def control_cycle(self):
        """
        Infinite loop: decide → yellow → all-red → next green → repeat.
        Cancelled externally when simulation stops.
        """
        while True:
            # -- Safe point: consume any pending emergency signal ----------
            # SimulationManager writes to self.pending_emergency instead of
            # mutating state directly, so we apply it here in one place.
            if self.pending_emergency:
                evt = self.pending_emergency
                self.pending_emergency = {}          # clear immediately
                axis = evt["axis"]
                self._set_green(axis)
                self.metrics['emergency_activations'] += 1
                logger.warning(f"AUTO EMERGENCY applied: {evt['type']} on {evt['location']} → {axis} green")
                # Clear cross-traffic after consuming the signal
                for road in self.ROADS:
                    if road != evt["location"]:
                        self.sensors[road].vehicle_count = max(
                            0, self.sensors[road].vehicle_count - 10
                        )
                await self._run_green_phase()
                self._update_metrics()
                continue

            # Wait during yellow or a full-red pause
            if self.state in (TrafficLightState.YELLOW, TrafficLightState.RED):
                if self.current_green is None:
                    await asyncio.sleep(0.5)
                    continue
                if self.state == TrafficLightState.YELLOW:
                    await asyncio.sleep(0.5)
                    continue

            next_green = await self.smart_decision()

            # First time or same axis — stay green, process vehicles
            if self.current_green is None or self.current_green == next_green:
                if self.current_green is None:
                    self._set_green(next_green)
                await self._run_green_phase()
                self._update_metrics()
                continue

            # ---- Transition: current → YELLOW → ALL RED → next GREEN ----
            self.last_switch_time = time.time()

            # YELLOW
            self.state = TrafficLightState.YELLOW
            for road in self.AXES[self.current_green]:
                self.road_light_states[road] = TrafficLightState.YELLOW
            yellow = getattr(cfg, 'YELLOW_DURATION', 4.5)
            logger.info(f"YELLOW on {self.current_green} for {yellow}s")
            await asyncio.sleep(yellow)

            # ALL RED clearance
            for road in self.ROADS:
                self.road_light_states[road] = TrafficLightState.RED
            self.state = TrafficLightState.RED
            all_red = getattr(cfg, 'ALL_RED_DURATION', 2)
            logger.info(f"ALL RED for {all_red}s")
            await asyncio.sleep(all_red)

            # NEW GREEN
            self._set_green(next_green)
            logger.info(f"GREEN on {self.current_green}")

            await self._run_green_phase()
            self._update_metrics()

            # RL update
            if self.rl_optimizer and self.last_state and self.last_action:
                volumes = {r: self.sensors[r].vehicle_count for r in self.ROADS}
                reward     = self.rl_optimizer.calculate_reward(volumes, self.wait_times)
                next_state = self.rl_optimizer.get_state(volumes, self.skip_counter)
                self.rl_optimizer.update(self.last_state, self.last_action,
                                         reward, next_state)

            # GA evolution (only after enough history)
            if self.ga_optimizer and len(self.history) > 50:
                if self.ga_population is None:
                    self.ga_population = self.ga_optimizer.create_population()
                self.ga_population = self.ga_optimizer.evolve(
                    self.ga_population, list(self.history)
                )

    # ------------------------------------------------------------------ #
    #  Green-phase helpers                                                 #
    # ------------------------------------------------------------------ #

    def _set_green(self, axis: str):
        self.current_green = axis
        self.state = TrafficLightState.GREEN
        for road in self.AXES[axis]:
            self.road_light_states[road] = TrafficLightState.GREEN
            self.wait_times[road] = 0        # cars on this road start moving — reset wait
        for road in self.ROADS:
            if road not in self.AXES[axis]:
                self.road_light_states[road] = TrafficLightState.RED

    async def _run_green_phase(self):
        """Let vehicles pass for the calculated duration."""
        duration   = self._calculate_green_duration()
        start      = time.time()

        while time.time() - start < duration:
            await self._process_green_tick()
            await asyncio.sleep(1)

            # Early exit if the axis clears completely
            axis_traffic = sum(
                self.sensors[r].vehicle_count for r in self.AXES[self.current_green]
            )
            if axis_traffic == 0:
                break

    async def _process_green_tick(self):
        """Move vehicles through the intersection for the green roads."""

        # GREEN roads: move vehicles through
        for road in self.AXES[self.current_green]:
            sensor = self.sensors[road]
            if sensor.vehicle_count <= 0:
                continue

            # Pass rate scales with congestion
            passed = 4 if sensor.vehicle_count > 30 else (
                     3 if sensor.vehicle_count > 15 else 2)
            passed = min(passed, sensor.vehicle_count)

            sensor.remove_vehicles(passed)
            self.metrics['total_throughput'] += passed

        # RED roads only: accumulate wait time (+1 second per tick)
        # Green roads already had their wait reset to 0 in _set_green(),
        # so we only penalise roads that are actually sitting at red.
        for road in self.ROADS:
            if road not in self.AXES[self.current_green]:
                if self.sensors[road].vehicle_count > 0:
                    self.wait_times[road] += 1

    def _calculate_green_duration(self) -> int:
        """Decide how many seconds the current axis should stay green."""
        axis_volume = sum(
            self.sensors[r].vehicle_count for r in self.AXES[self.current_green]
        )
        min_g = getattr(cfg, 'MIN_GREEN_DURATION', 10)
        max_g = getattr(cfg, 'MAX_GREEN_DURATION', 40)

        # Let ML override if available
        if (self.ml_predictor and
                getattr(self.ml_predictor, 'is_trained', False) and
                getattr(self.ml_predictor, 'last_prediction', None)):
            congestion = self.ml_predictor.last_prediction.get('congestion_level', 1)
            return self.ml_predictor.get_optimal_duration(axis_volume, congestion)

        # Fallback: volume-based
        if axis_volume > 40:
            duration = max_g
        elif axis_volume > 20:
            duration = (max_g + min_g) // 2
        elif axis_volume > 5:
            duration = min_g + 5
        else:
            duration = min_g

        # Weather + time-of-day modifiers
        duration = self._apply_weather(duration)
        duration = self._apply_time_modifier(duration)
        return max(min_g, min(max_g, duration))

    def _apply_weather(self, duration: int) -> int:
        if self.emergency_detector and hasattr(self.emergency_detector, 'get_weather_modifier'):
            return int(duration * self.emergency_detector.get_weather_modifier())
        return duration

    def _apply_time_modifier(self, duration: int) -> float:
        if not self.emergency_detector:
            return duration
        active = getattr(self.emergency_detector, 'active_emergencies', [])
        for e in active:
            if e.type.value == 'time_based':
                if 'rush hour' in e.description.lower():
                    return int(duration * 1.3)
                if 'school zone' in e.description.lower():
                    return int(duration * 0.8)
        return duration

    # ------------------------------------------------------------------ #
    #  Metrics                                                             #
    # ------------------------------------------------------------------ #

    def _update_metrics(self):
        total_cars = sum(s.vehicle_count for s in self.sensors.values())
        total_wait = sum(self.wait_times.values())

        if total_cars > 0:
            self.metrics['average_wait_time'] = total_wait / total_cars

        self.history.append({r: s.vehicle_count for r, s in self.sensors.items()})

        if total_cars > cfg.CONGESTION_THRESHOLD:
            self.metrics['congestion_events'] += 1

    # ------------------------------------------------------------------ #
    #  Status snapshot (used by API and WebSocket)                        #
    # ------------------------------------------------------------------ #

    def get_status(self) -> Dict:
        status = {
            'intersection':  self.name,
            'state':         self.state.value,
            'current_green': self.current_green,
            'skip_counter':  self.skip_counter,
            'traffic':      {r: s.vehicle_count for r, s in self.sensors.items()},
            'flow_rates':    self.get_traffic_flow(),
            'wait_times':    self.wait_times,
            'metrics':       self.metrics,
            'light_states': {r: st.value for r, st in self.road_light_states.items()},
        }
        if self.emergency_detector:
            status['active_emergencies'] = [
                {
                    'type':        e.type.value,
                    'location':    e.location,
                    'priority':    e.priority,
                    'description': e.description,
                    'timestamp':   e.timestamp.isoformat(),
                }
                for e in self.emergency_detector.get_active_emergencies()
            ]
            status['weather_condition'] = getattr(
                self.emergency_detector, 'weather_conditions', 'clear'
            )
        return status
