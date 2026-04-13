from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import json
import random
from datetime import datetime
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import configuration
from backend import config
from backend.traffic_controller import TrafficIntersection, TrafficLightState
from backend.ml_predictor import TrafficPredictor
from backend.optimization import ReinforcementLearningOptimizer, GeneticAlgorithmOptimizer
from backend.database import TrafficDatabase
from backend.emergency_detector import EmergencyDetector

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)

# Mount static files
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "frontend"), name="static")

# To serve static files from root:
@app.get("/styles.css")
async def serve_css():
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).parent.parent / "frontend" / "styles.css")

@app.get("/script.js")  
async def serve_js():
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).parent.parent / "frontend" / "script.js")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = TrafficDatabase(Path(config.DB_PATH))

# Initialize components
ml_predictor = TrafficPredictor(history_window=config.ML_HISTORY_WINDOW)
rl_optimizer = ReinforcementLearningOptimizer(
    learning_rate=config.RL_LEARNING_RATE,
    discount_factor=config.RL_DISCOUNT_FACTOR
)
ga_optimizer = GeneticAlgorithmOptimizer(population_size=config.GA_POPULATION_SIZE)
emergency_detector = EmergencyDetector(config)

# Create intersection controller
intersection = TrafficIntersection(
    name="Main Intersection",
    ml_predictor=ml_predictor,
    rl_optimizer=rl_optimizer,
    ga_optimizer=ga_optimizer,
    emergency_detector=emergency_detector
)

# Background tasks
simulation_running = False
spawn_task = None
control_task = None
emergency_task = None

class SensorData(BaseModel):
    north: int
    south: int
    east: int
    west: int
    timestamp: Optional[str] = None

class EmergencyEvent(BaseModel):
    type: str
    location: str
    priority: int


# ============== BACKGROUND TASKS ==============

async def spawn_vehicles():
    """Background task to spawn vehicles dynamically"""
    global simulation_running
    logger.info("🚗 Vehicle spawner started")
    try:
        while simulation_running:
            try:
                # Dynamic spawn rate based on time of day
                hour = datetime.now().hour
                if 7 <= hour <= 9 or 17 <= hour <= 19:
                    spawn_rate = config.SPAWN_RATE_RUSH_HOUR
                    rush_factor = 1.5
                elif 23 <= hour or hour <= 5:
                    spawn_rate = config.SPAWN_RATE_NIGHT
                    rush_factor = 0.5
                else:
                    spawn_rate = config.SPAWN_RATE_NORMAL
                    rush_factor = 1.0
                
                logger.debug(f"Spawning vehicles with rate: {spawn_rate}s, rush_factor: {rush_factor}")
                await asyncio.sleep(spawn_rate)
                
                if not simulation_running:
                    break
                
                # Spawn vehicles with realistic distribution
                for road in intersection.roads:
                    if road in ['North', 'South'] and rush_factor > 1:
                        increment = random.randint(3, 6)
                    elif rush_factor < 1:
                        increment = random.randint(0, 2)
                    else:
                        increment = random.randint(1, 4)
                    
                    # Add vehicles to the sensor
                    intersection.sensors[road].add_vehicles(increment)
                    logger.info(f"🚗 Spawned {increment} vehicles on {road} (total: {intersection.sensors[road].vehicle_count})")
                    
                # Save traffic data periodically
                if random.random() < 0.1:
                    db.save_traffic_data(
                        {road: sensor.vehicle_count for road, sensor in intersection.sensors.items()},
                        intersection.current_green
                    )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Vehicle spawner error: {e}")
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("🛑 Vehicle spawner cancelled")


async def emergency_handler():
    """Background task to handle random emergency events"""
    global simulation_running
    logger.info("🚨 Emergency handler started")
    try:
        while simulation_running:
            try:
                if random.random() < config.EMERGENCY_PROBABILITY:
                    emergency_type = random.choice(["accident", "ambulance", "fire_truck"])
                    location = random.choice(intersection.roads)
                    logger.warning(f"🚨 AUTO EMERGENCY: {emergency_type} on {location}")
                    
                    db.save_emergency_event(emergency_type, location, priority=3)
                    
                    emergency_axis = 'NS' if location in ['North', 'South'] else 'EW'
                    intersection.current_green = emergency_axis
                    
                    for road in intersection.roads:
                        if road != location:
                            intersection.sensors[road].vehicle_count = max(0, 
                                intersection.sensors[road].vehicle_count - 10)
                    
                    intersection.metrics['emergency_activations'] += 1
                    
                    await asyncio.sleep(config.EMERGENCY_PRIORITY_DURATION)
                
                if emergency_detector:
                    emergency_detector.cleanup_expired_emergencies()
                    
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Emergency handler error: {e}")
                await asyncio.sleep(10)
    except asyncio.CancelledError:
        logger.info("🛑 Emergency handler cancelled")


# ============== API ENDPOINTS ==============

@app.on_event("startup")
async def startup_event():
    """Initialize ML model on startup"""
    logger.info("=" * 60)
    logger.info(f"Initializing {config.APP_NAME} v{config.APP_VERSION}...")
    logger.info("=" * 60)
    
    # Train ML predictor
    logger.info(f"Training ML models with {config.ML_TRAINING_SAMPLES} samples...")
    ml_predictor.generate_training_data(config.ML_TRAINING_SAMPLES)
    logger.info("ML models trained successfully!")
    
    # Log system configuration
    logger.info(f"Database: {config.DB_PATH}")
    logger.info(f"Port: {config.PORT}")
    logger.info(f"Log Level: {config.LOG_LEVEL}")
    logger.info("=" * 60)
    logger.info("System ready! Visit http://localhost:3000")
    logger.info("=" * 60)


@app.post("/api/simulation/start")
async def start_simulation():
    """Start the traffic simulation"""
    global simulation_running, spawn_task, control_task, emergency_task
    
    if simulation_running:
        return {"status": "already_running", "message": "Simulation is already active"}
    
    simulation_running = True
    
    # Reset some state to ensure vehicles spawn
    for road in intersection.roads:
        intersection.sensors[road].vehicle_count = random.randint(5, 15)
        logger.info(f"Initialized {road} with {intersection.sensors[road].vehicle_count} vehicles")
    
    # Launch as proper asyncio tasks
    spawn_task = asyncio.create_task(spawn_vehicles())
    control_task = asyncio.create_task(intersection.control_cycle())
    emergency_task = asyncio.create_task(emergency_handler())
    
    logger.info("🚦 Simulation started - All systems active")
    
    return {"status": "started", "message": "Smart traffic control system activated"}


@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop the traffic simulation"""
    global simulation_running, spawn_task, control_task, emergency_task
    simulation_running = False
    
    # Cancel running asyncio tasks
    for task in [spawn_task, control_task, emergency_task]:
        if task and not task.done():
            task.cancel()
    spawn_task = control_task = emergency_task = None
    
    # Reset intersection state
    intersection.current_green = None
    intersection.state = TrafficLightState.RED
    for road in intersection.roads:
        intersection.road_light_states[road] = TrafficLightState.RED
        intersection.sensors[road].vehicle_count = 0
        intersection.wait_times[road] = 0
    intersection.metrics = {
        'total_throughput': 0,
        'average_wait_time': 0,
        'congestion_events': 0,
        'emergency_activations': 0
    }

    logger.info("🛑 Simulation stopped")
    return {"status": "stopped", "message": "Simulation stopped"}


@app.get("/api/state")
async def get_state():
    """Get current system state"""
    status = intersection.get_status()
    
    # Add ML predictions
    predictions = None
    if ml_predictor.is_trained:
        try:
            current_time = datetime.now()
            predictions = await ml_predictor.predict_traffic(
                status['traffic'],
                current_time.hour,
                current_time.weekday()
            )
            db.save_prediction(predictions)
        except Exception as e:
            logger.error(f"Prediction error: {e}")
    
    # Save metrics periodically
    if random.random() < 0.1:
        db.save_metrics(intersection.metrics)
    
    return {
        **status,
        "predictions": predictions,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/sensor/update")
async def update_sensor_data(data: SensorData):
    """Update sensor data from external sources (IoT devices)"""
    traffic_data = {
        "North": data.north,
        "South": data.south,
        "East": data.east,
        "West": data.west
    }
    await intersection.update_sensors(traffic_data)
    return {"status": "updated", "data": traffic_data}


@app.post("/api/emergency")
async def report_emergency(emergency: EmergencyEvent):
    """Handle manual emergency reports"""
    logger.warning(f"🚨 MANUAL EMERGENCY: {emergency.type} at {emergency.location} (Priority {emergency.priority})")
    
    db.save_emergency_event(emergency.type, emergency.location, emergency.priority)
    
    emergency_axis = 'NS' if emergency.location in ['North', 'South'] else 'EW'
    
    intersection.current_green = emergency_axis
    intersection.state = TrafficLightState.GREEN
    
    for road in intersection.roads:
        if road in ['North', 'South'] and emergency_axis == 'NS':
            intersection.road_light_states[road] = TrafficLightState.GREEN
        elif road in ['East', 'West'] and emergency_axis == 'EW':
            intersection.road_light_states[road] = TrafficLightState.GREEN
        else:
            intersection.road_light_states[road] = TrafficLightState.RED
    
    intersection.metrics['emergency_activations'] += 1
    db.save_metrics(intersection.metrics)
    
    cleared_vehicles = 0
    for road in intersection.roads:
        if road != emergency.location:
            reduction = min(15, intersection.sensors[road].vehicle_count)
            intersection.sensors[road].vehicle_count = max(0, 
                intersection.sensors[road].vehicle_count - reduction)
            cleared_vehicles += reduction
    
    if emergency_detector:
        from backend.emergency_detector import EmergencyEvent as DetectorEmergencyEvent, EmergencyType
        detector_emergency = DetectorEmergencyEvent(
            type=EmergencyType.ACCIDENT if emergency.type == "accident" else EmergencyType.AMBULANCE,
            location=emergency.location,
            priority=emergency.priority,
            timestamp=datetime.now(),
            description=f"MANUAL: {emergency.type} at {emergency.location}",
            duration=config.EMERGENCY_PRIORITY_DURATION,
            active=True
        )
        emergency_detector.active_emergencies.append(detector_emergency)
    
    asyncio.create_task(reset_after_emergency(emergency_axis, emergency.location))
    
    return {
        "status": "acknowledged", 
        "action": f"🟢 GREEN LIGHT for {emergency.location} direction! {cleared_vehicles} vehicles cleared from path.",
        "axis": emergency_axis,
        "duration": config.EMERGENCY_PRIORITY_DURATION
    }


async def reset_after_emergency(emergency_axis: str, location: str):
    """Reset traffic lights after emergency priority duration"""
    await asyncio.sleep(config.EMERGENCY_PRIORITY_DURATION)
    
    if intersection.current_green == emergency_axis:
        logger.info(f"🔄 Emergency mode ending for {location}, returning to normal operation")
        intersection.current_green = None
        intersection.state = TrafficLightState.RED
        if emergency_detector:
            emergency_detector.active_emergencies = [
                e for e in emergency_detector.active_emergencies 
                if e.location != location or not e.active
            ]


@app.get("/api/emergencies")
async def get_emergency_log(limit: int = 20):
    """Get emergency event log"""
    if emergency_detector:
        emergencies = emergency_detector.get_emergency_log(limit)
        return {
            "emergencies": [
                {
                    "type": e.type.value,
                    "location": e.location,
                    "priority": e.priority,
                    "description": e.description,
                    "timestamp": e.timestamp.isoformat(),
                    "active": e.active
                }
                for e in emergencies
            ],
            "weather_condition": emergency_detector.weather_conditions
        }
    return {"emergencies": [], "weather_condition": "clear"}


@app.get("/api/metrics")
async def get_metrics():
    """Get system performance metrics"""
    return intersection.metrics


@app.get("/api/analytics/summary")
async def get_analytics_summary(hours: int = 1):
    """Get analytics summary for last N hours"""
    summary = db.get_metrics_summary(hours)
    return {
        "hours": hours,
        "data": summary,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/analytics/traffic")
async def get_traffic_history(limit: int = 100):
    """Get recent traffic data"""
    traffic_data = db.get_recent_traffic(limit)
    return {
        "count": len(traffic_data),
        "data": traffic_data
    }


@app.get("/api/analytics/emergencies")
async def get_emergency_history(hours: int = 24):
    """Get emergency events history"""
    emergencies = db.get_emergency_events(hours)
    return {
        "hours": hours,
        "count": len(emergencies),
        "events": emergencies
    }


@app.get("/api/optimization/recommendations")
async def get_recommendations():
    """Get optimization recommendations"""
    recommendations = []
    
    if intersection.metrics['average_wait_time'] > 30:
        recommendations.append({
            "type": "increase_green_duration",
            "reason": f"High average wait time: {intersection.metrics['average_wait_time']:.1f}s",
            "suggestion": "Increase green light duration during peak hours"
        })
    
    if intersection.metrics['congestion_events'] > 10:
        recommendations.append({
            "type": "reroute_traffic",
            "reason": f"Multiple congestion events: {intersection.metrics['congestion_events']}",
            "suggestion": "Consider dynamic lane management or alternate routes"
        })
    
    traffic = intersection.get_status()['traffic']
    ns_total = traffic.get('North', 0) + traffic.get('South', 0)
    ew_total = traffic.get('East', 0) + traffic.get('West', 0)
    
    if ns_total > ew_total * 1.5:
        recommendations.append({
            "type": "balance_traffic",
            "reason": f"North-South has {ns_total} vehicles, East-West has {ew_total}",
            "suggestion": "Extend green time for North-South axis"
        })
    elif ew_total > ns_total * 1.5:
        recommendations.append({
            "type": "balance_traffic",
            "reason": f"East-West has {ew_total} vehicles, North-South has {ns_total}",
            "suggestion": "Extend green time for East-West axis"
        })
    
    if rl_optimizer.q_table:
        try:
            best_action = max(rl_optimizer.actions, 
                             key=lambda a: max(rl_optimizer.q_table.get(a, {0:0}).values()))
            recommendations.append({
                "type": "rl_optimal_action",
                "reason": "Based on reinforcement learning",
                "suggestion": f"Optimal action pattern: {best_action}"
            })
        except:
            pass
    
    return recommendations


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    logger.info("🔌 WebSocket client connected")
    
    try:
        while True:
            if simulation_running:
                state = await get_state()
                await websocket.send_json(state)
            else:
                await websocket.send_json({"simulation_stopped": True})
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    """Serve frontend"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    try:
        with open(frontend_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Frontend file not found at {frontend_path}")
        return HTMLResponse(content="""
            <html>
                <body>
                    <h1>🚦 Smart Traffic Control System</h1>
                    <p>Frontend file not found. Please ensure index.html exists in the frontend folder.</p>
                </body>
            </html>
        """, status_code=404)


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level=config.LOG_LEVEL.lower())