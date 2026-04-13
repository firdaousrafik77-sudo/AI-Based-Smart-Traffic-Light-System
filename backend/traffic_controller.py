from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import asyncio
import time
import random
from datetime import datetime
import logging
from collections import deque
import sys
from pathlib import Path

# Import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrafficLightState(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

@dataclass
class RoadSensor:
    """Simulated sensor for a road"""
    name: str
    vehicle_count: int = 0
    waiting_time: float = 0
    last_update: float = 0
    last_flow_calc_time: float = 0  # Track when flow was last calculated
    last_count: int = 0  # Track previous count for flow calculation
    
    def __post_init__(self):
        """Initialize timestamps"""
        current_time = time.time()
        self.last_update = current_time
        self.last_flow_calc_time = current_time
        self.last_count = 0
    
    def update(self, count: int):
        """Update vehicle count and track changes"""
        current_time = time.time()
        
        # Store previous values for flow calculation
        self.last_count = self.vehicle_count
        self.last_flow_calc_time = self.last_update
        
        self.vehicle_count = count
        self.last_update = current_time
    
    def add_vehicles(self, increment: int):
        """Add vehicles to the count"""
        current_time = time.time()
        
        # Store previous values for flow calculation
        self.last_count = self.vehicle_count
        self.last_flow_calc_time = self.last_update
        
        self.vehicle_count += increment
        self.last_update = current_time
    
    def remove_vehicles(self, count: int):
        """Remove vehicles that passed through"""
        self.vehicle_count = max(0, self.vehicle_count - count)
    
    def get_flow_rate(self) -> float:
        """Calculate vehicles per minute based on actual changes"""
        current_time = time.time()
        
        # Calculate time difference since last update
        time_diff = current_time - self.last_flow_calc_time
        
        # If no time has passed or no vehicles, return 0
        if time_diff < 0.1:
            return 0.0
        
        # Calculate the change in vehicle count (positive for incoming, negative for outgoing)
        # For flow rate, we want the rate of vehicles that have passed through
        # Since vehicles are removed in process_green_phase, we track the decrease
        count_change = self.last_count - self.vehicle_count
        
        # If count increased, that's incoming vehicles - use that for incoming flow
        if count_change < 0:
            count_change = abs(count_change)
        
        # Calculate flow rate (vehicles per minute)
        flow_rate = (count_change / time_diff) * 60
        
        # Update last values for next calculation
        self.last_count = self.vehicle_count
        self.last_flow_calc_time = current_time
        
        return max(0.0, flow_rate)

class TrafficIntersection:
    """Main intersection controller with OOP design"""
    
    def __init__(self, name: str, ml_predictor=None, rl_optimizer=None, ga_optimizer=None, emergency_detector=None):
        self.name = name
        self.roads = ["North", "South", "East", "West"]
        self.axes = {"NS": ["North", "South"], "EW": ["East", "West"]}
        self.sensors = {road: RoadSensor(road) for road in self.roads}
        self.current_green: Optional[str] = None
        self.yellow_timer = 0
        self.yellow_start_time = 0
        self.state = TrafficLightState.RED
        # Per-road light states
        self.road_light_states = {road: TrafficLightState.RED for road in self.roads}
        self.skip_counter = {axis: 0 for axis in self.axes}
        self.wait_times = {road: 0 for road in self.roads}
        self.history = deque(maxlen=100)
        
        # ML and optimization components
        self.ml_predictor = ml_predictor
        self.rl_optimizer = rl_optimizer
        self.ga_optimizer = ga_optimizer
        self.emergency_detector = emergency_detector
        self.ga_population = None
        self.last_state = None
        self.last_action = None
        
        # Track last switch time to prevent rapid cycling
        self.last_switch_time = 0
        self.min_cycle_duration = 10
        
        # Performance metrics
        self.metrics = {
            'total_throughput': 0,
            'average_wait_time': 0,
            'congestion_events': 0,
            'emergency_activations': 0
        }
        
        # Initialize with North-South green
        self._initialize_green_state()
        
    def _initialize_green_state(self):
        """Initialize the intersection with North-South green lights"""
        self.current_green = 'NS'
        self.state = TrafficLightState.GREEN
        
        # Set North and South to GREEN
        self.road_light_states['North'] = TrafficLightState.GREEN
        self.road_light_states['South'] = TrafficLightState.GREEN
        
        # Set East and West to RED
        self.road_light_states['East'] = TrafficLightState.RED
        self.road_light_states['West'] = TrafficLightState.RED
        
        logger.info("🟢 INITIAL STATE: North-South GREEN, East-West RED")
        
    async def update_sensors(self, traffic_data: Dict[str, int]):
        """Update sensor readings"""
        for road, count in traffic_data.items():
            self.sensors[road].update(count)
            
    def get_traffic_flow(self) -> Dict[str, float]:
        """Get current flow rates"""
        return {road: sensor.get_flow_rate() for road, sensor in self.sensors.items()}
    
    async def smart_decision(self) -> str:
        """Make smart decision using ML predictions and optimization"""
        
        if self.state == TrafficLightState.YELLOW:
            logger.debug("Cannot make decision during yellow phase")
            return self.current_green if self.current_green else 'NS'
        
        current_time = time.time()
        if self.last_switch_time > 0 and (current_time - self.last_switch_time) < self.min_cycle_duration:
            return self.current_green if self.current_green else 'NS'
        
        current_time_of_day = datetime.now()
        hour = current_time_of_day.hour
        day = current_time_of_day.weekday()
        
        predictions = None
        if self.ml_predictor:
            current_traffic = {road: self.sensors[road].vehicle_count for road in self.roads}
            predictions = await self.ml_predictor.predict_traffic(current_traffic, hour, day)
            logger.debug(f"ML Predictions: {predictions}")
        
        traffic_volumes = {road: self.sensors[road].vehicle_count for road in self.roads}
        
        # Emergency detection
        if self.emergency_detector:
            emergency = self.emergency_detector.check_all_emergencies(traffic_volumes, predictions)
            if emergency:
                self.metrics['emergency_activations'] += 1
                
                if emergency.type.value in ['ambulance', 'fire_truck']:
                    priority_axis = 'NS' if emergency.location in ['North', 'South'] else 'EW'
                    logger.warning(f"🚨 {emergency.type.value.upper()} EMERGENCY: {emergency.description}")
                    return priority_axis
                elif emergency.type.value == 'accident':
                    accident_axis = 'NS' if emergency.location in ['North', 'South'] else 'EW'
                    return 'EW' if accident_axis == 'NS' else 'NS'
                elif emergency.type.value in ['congestion', 'predictive']:
                    emergency_axis = 'NS' if emergency.location in ['North', 'South'] else 'EW'
                    logger.warning(f"⚠️ {emergency.type.value.upper()}: {emergency.description}")
                    return emergency_axis
                elif emergency.type.value == 'time_based':
                    logger.info(f"⏰ TIME-BASED PRIORITY: {emergency.description}")
                elif emergency.type.value == 'weather':
                    logger.info(f"🌧️ WEATHER ALERT: {emergency.description}")
        
        # RL decision making
        if self.rl_optimizer:
            state = self.rl_optimizer.get_state(traffic_volumes, self.skip_counter)
            action = self.rl_optimizer.choose_action(state)
            
            self.last_state = state
            self.last_action = action
            
            if action == 'adaptive_cycle':
                if self.ga_optimizer and self.ga_population:
                    best_timing = max(self.ga_population, 
                                    key=lambda x: self.ga_optimizer.fitness(x, list(self.history)))
                    if sum(traffic_volumes.values()) > 50:
                        return self.current_green if self.current_green else 'NS'
            elif action == 'emergency':
                return 'NS' if max(traffic_volumes, key=traffic_volumes.get) in ['North', 'South'] else 'EW'
            elif action in ['NS', 'EW']:
                return action
        
        # Default decision logic
        ns_traffic = traffic_volumes['North'] + traffic_volumes['South']
        ew_traffic = traffic_volumes['East'] + traffic_volumes['West']
        
        if self.current_green == 'NS' and ew_traffic > ns_traffic * 1.2:
            logger.info(f"Forcing switch: EW traffic ({ew_traffic}) > NS traffic ({ns_traffic})")
            return 'EW'
        elif self.current_green == 'EW' and ns_traffic > ew_traffic * 1.2:
            logger.info(f"Forcing switch: NS traffic ({ns_traffic}) > EW traffic ({ew_traffic})")
            return 'NS'
        
        for axis in self.axes:
            if axis != self.current_green:
                self.skip_counter[axis] += 1
            else:
                self.skip_counter[axis] = 0
                
        if self.skip_counter['NS'] >= 4:
            logger.info("Skip counter forcing NS green")
            return 'NS'
        if self.skip_counter['EW'] >= 4:
            logger.info("Skip counter forcing EW green")
            return 'EW'
            
        if predictions:
            ns_pred = predictions['North'] + predictions['South']
            ew_pred = predictions['East'] + predictions['West']
            ns_score = ns_traffic * 0.6 + ns_pred * 0.4
            ew_score = ew_traffic * 0.6 + ew_pred * 0.4
        else:
            ns_score = ns_traffic
            ew_score = ew_traffic
            
        if self.current_green == 'NS' and ew_score > ns_score * 1.5:
            return 'EW'
        elif self.current_green == 'EW' and ns_score > ew_score * 1.5:
            return 'NS'
            
        return self.current_green if self.current_green else ('NS' if ns_score >= ew_score else 'EW')
    
    async def control_cycle(self):
        """Main control cycle with adaptive timing"""
        
        while True:
            if self.state == TrafficLightState.YELLOW:
                await asyncio.sleep(0.5)
                continue
            
            if self.state == TrafficLightState.RED and self.current_green is None:
                await asyncio.sleep(0.5)
                continue
            
            next_green = await self.smart_decision()
            
            if self.current_green is None:
                self.current_green = next_green
                self.state = TrafficLightState.GREEN
                for road in self.axes[self.current_green]:
                    self.road_light_states[road] = TrafficLightState.GREEN
                for road in self.roads:
                    if road not in self.axes[self.current_green]:
                        self.road_light_states[road] = TrafficLightState.RED
                logger.info(f"🟢 INITIAL GREEN light on {self.current_green}")
                
                green_duration = self.calculate_green_duration()
                green_start = time.time()
                while time.time() - green_start < green_duration:
                    await self.process_green_phase()
                    await asyncio.sleep(1)
                    axis_traffic = sum(self.sensors[road].vehicle_count for road in self.axes[self.current_green])
                    if axis_traffic == 0:
                        break
                self.update_metrics()
                continue
            
            if self.current_green == next_green:
                await asyncio.sleep(1)
                continue
            
            # Transition: GREEN -> YELLOW -> ALL RED -> Next GREEN
            self.last_switch_time = time.time()
            
            # YELLOW PHASE
            self.state = TrafficLightState.YELLOW
            self.yellow_start_time = time.time()
            
            current_green_roads = self.axes[self.current_green]
            for road in current_green_roads:
                self.road_light_states[road] = TrafficLightState.YELLOW
            
            yellow_duration = getattr(config, 'YELLOW_DURATION', 4.5)
            logger.info(f"🟡 YELLOW light on {self.current_green} for {yellow_duration}s")
            await asyncio.sleep(yellow_duration)
            
            # ALL RED CLEARANCE
            all_red_duration = getattr(config, 'ALL_RED_DURATION', 2)
            
            if all_red_duration > 0:
                for road in self.roads:
                    self.road_light_states[road] = TrafficLightState.RED
                self.state = TrafficLightState.RED
                logger.info(f"🔴 ALL RED clearance for {all_red_duration}s")
                await asyncio.sleep(all_red_duration)
            
            # SWITCH TO NEW GREEN AXIS
            self.current_green = next_green
            self.state = TrafficLightState.GREEN
            
            next_green_roads = self.axes[next_green]
            for road in next_green_roads:
                self.road_light_states[road] = TrafficLightState.GREEN
            
            for road in self.roads:
                if road not in next_green_roads:
                    self.road_light_states[road] = TrafficLightState.RED
            
            logger.info(f"🟢 GREEN light on {self.current_green}")
            
            # GREEN PHASE
            green_duration = self.calculate_green_duration()
            green_start = time.time()
            
            while time.time() - green_start < green_duration:
                await self.process_green_phase()
                await asyncio.sleep(1)
                
                axis_roads = self.axes[self.current_green]
                axis_traffic = sum(self.sensors[road].vehicle_count for road in axis_roads)
                if axis_traffic == 0:
                    logger.info(f"Early switch: No traffic on {self.current_green}")
                    break
            
            self.update_metrics()
            
            if self.rl_optimizer and self.last_state and self.last_action:
                reward = self.rl_optimizer.calculate_reward(
                    {road: self.sensors[road].vehicle_count for road in self.roads},
                    self.wait_times
                )
                next_state = self.rl_optimizer.get_state(
                    {road: self.sensors[road].vehicle_count for road in self.roads},
                    self.skip_counter
                )
                self.rl_optimizer.update(self.last_state, self.last_action, reward, next_state)
            
            if self.ga_optimizer and len(self.history) > 50:
                self.ga_population = self.ga_optimizer.evolve(
                    self.ga_population or self.ga_optimizer.create_population(),
                    list(self.history)
                )
    
    def calculate_green_duration(self) -> int:
        """Calculate optimal green duration based on multiple factors"""
        if not self.current_green:
            return getattr(config, 'MIN_GREEN_DURATION', 10)
            
        axis_roads = self.axes[self.current_green]
        axis_traffic = sum(self.sensors[road].vehicle_count for road in axis_roads)
        
        min_green = getattr(config, 'MIN_GREEN_DURATION', 10)
        max_green = getattr(config, 'MAX_GREEN_DURATION', 40)
        
        if self.ml_predictor and hasattr(self.ml_predictor, 'is_trained') and self.ml_predictor.is_trained:
            congestion_level = 1
            if hasattr(self.ml_predictor, 'last_prediction') and self.ml_predictor.last_prediction:
                congestion_level = self.ml_predictor.last_prediction.get('congestion_level', 1)
            if hasattr(self.ml_predictor, 'get_optimal_duration'):
                return self.ml_predictor.get_optimal_duration(axis_traffic, congestion_level)
        
        if axis_traffic > 40:
            duration = max_green
        elif axis_traffic > 20:
            duration = int((max_green + min_green) / 2)
        elif axis_traffic > 5:
            duration = min_green + 5
        else:
            duration = min_green
            
        duration = self.apply_weather_modifier(duration)
        
        time_modifier = self.get_time_based_modifier()
        if time_modifier != 1.0:
            duration = int(duration * time_modifier)
            duration = max(min_green, min(max_green, duration))
            
        return duration
    
    async def process_green_phase(self):
        """Process vehicles during green phase - UPDATED to track flow properly"""
        if not self.current_green:
            return
            
        axis_roads = self.axes[self.current_green]
        
        for road in axis_roads:
            sensor = self.sensors[road]
            if sensor.vehicle_count > 0:
                # Pass rate based on congestion
                if sensor.vehicle_count > 30:
                    passed = 4
                elif sensor.vehicle_count > 15:
                    passed = 3
                else:
                    passed = 2
                    
                passed = min(passed, sensor.vehicle_count)
                sensor.remove_vehicles(passed)  # Use remove_vehicles method
                self.metrics['total_throughput'] += passed
                
                # Decrease wait times for vehicles that passed
                if passed > 0:
                    self.wait_times[road] = max(0, self.wait_times[road] - (passed * 2))
                
                # Update wait times for remaining vehicles
                for r in self.roads:
                    if self.sensors[r].vehicle_count > 0:
                        self.wait_times[r] += 1
                        
    def update_metrics(self):
        """Update performance metrics"""
        total_cars = sum(sensor.vehicle_count for sensor in self.sensors.values())
        total_wait = sum(self.wait_times.values())
        
        if total_cars > 0:
            self.metrics['average_wait_time'] = total_wait / total_cars
            
        self.history.append({road: sensor.vehicle_count for road, sensor in self.sensors.items()})
        
        if total_cars > 60:
            self.metrics['congestion_events'] += 1
            
    def get_status(self) -> Dict:
        """Get current system status"""
        status = {
            'intersection': self.name,
            'state': self.state.value,
            'current_green': self.current_green,
            'skip_counter': self.skip_counter,
            'traffic': {road: sensor.vehicle_count for road, sensor in self.sensors.items()},
            'flow_rates': self.get_traffic_flow(),
            'metrics': self.metrics,
            'wait_times': self.wait_times,
            'light_states': {road: state.value for road, state in self.road_light_states.items()}
        }
        
        if self.emergency_detector:
            if hasattr(self.emergency_detector, 'get_active_emergencies'):
                status['active_emergencies'] = [
                    {
                        'type': e.type.value,
                        'location': e.location,
                        'priority': e.priority,
                        'description': e.description,
                        'timestamp': e.timestamp.isoformat()
                    }
                    for e in self.emergency_detector.get_active_emergencies()
                ]
            if hasattr(self.emergency_detector, 'weather_conditions'):
                status['weather_condition'] = self.emergency_detector.weather_conditions
        
        return status

    def handle_emergency_vehicle(self, emergency_type: str, location: str) -> str:
        """Handle emergency vehicle priority"""
        if emergency_type in ['ambulance', 'fire_truck']:
            priority_axis = 'NS' if location in ['North', 'South'] else 'EW'
            logger.warning(f"🚨 {emergency_type.upper()} EMERGENCY: Immediate priority to {priority_axis}")
            return priority_axis
        return self.current_green if self.current_green else 'NS'

    def handle_accident_detection(self, accident_road: str) -> str:
        """Handle accident by diverting traffic"""
        accident_axis = 'NS' if accident_road in ['North', 'South'] else 'EW'
        diversion_axis = 'EW' if accident_axis == 'NS' else 'NS'
        logger.warning(f"💥 ACCIDENT DETECTED on {accident_road}: Diverting traffic to {diversion_axis}")
        return diversion_axis

    def apply_weather_modifier(self, base_duration: int) -> int:
        """Apply weather-based timing modifications"""
        if self.emergency_detector and hasattr(self.emergency_detector, 'get_weather_modifier'):
            modifier = self.emergency_detector.get_weather_modifier()
            adjusted_duration = int(base_duration * modifier)
            if modifier < 1.0:
                logger.info(f"🌧️ Weather modifier applied: {modifier:.1f}x (duration: {base_duration}s → {adjusted_duration}s)")
            return adjusted_duration
        return base_duration

    def get_time_based_modifier(self) -> float:
        """Get timing modifier based on time of day"""
        if not self.emergency_detector:
            return 1.0

        if hasattr(self.emergency_detector, 'get_active_emergencies'):
            active_emergencies = self.emergency_detector.get_active_emergencies()
            time_emergencies = [e for e in active_emergencies if e.type.value == 'time_based']

            if time_emergencies:
                emergency = time_emergencies[0]
                if 'rush hour' in emergency.description.lower():
                    return 1.3
                elif 'school zone' in emergency.description.lower():
                    return 0.8

        return 1.0