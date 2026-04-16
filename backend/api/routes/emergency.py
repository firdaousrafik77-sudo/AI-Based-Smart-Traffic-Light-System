"""
Layer 5 - API Routes: Emergency reporting and log
"""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from ..dependencies import intersection, db, emergency_detector
from ...models.traffic   import TrafficLightState
from ...models.emergency import EmergencyType, EmergencyEvent
from ... import config

router = APIRouter(prefix="/api", tags=["emergency"])
logger = logging.getLogger(__name__)


# ---- Pydantic request model ------------------------------------------

class EmergencyRequest(BaseModel):
    """Body for POST /api/emergency"""
    type:     str   # "accident", "ambulance", "fire_truck"
    location: str   # "North", "South", "East", "West"
    priority: int   # 1-5


# ---- Endpoints -------------------------------------------------------

@router.post("/emergency")
async def report_emergency(request: EmergencyRequest):
    """
    Manually report an emergency.
    The system immediately gives green to the affected axis
    and clears vehicles from cross-traffic roads.
    """
    logger.warning(f"MANUAL EMERGENCY: {request.type} at "
                   f"{request.location} (priority {request.priority})")

    db.save_emergency_event(request.type, request.location, request.priority)

    axis = 'NS' if request.location in ('North', 'South') else 'EW'

    # Override the intersection lights immediately
    intersection.current_green = axis
    intersection.state = TrafficLightState.GREEN
    for road in intersection.ROADS:
        if (road in ('North', 'South') and axis == 'NS') or \
           (road in ('East', 'West')   and axis == 'EW'):
            intersection.road_light_states[road] = TrafficLightState.GREEN
        else:
            intersection.road_light_states[road] = TrafficLightState.RED

    intersection.metrics['emergency_activations'] += 1
    db.save_metrics(intersection.metrics)

    # Clear some vehicles from the cross-traffic roads
    cleared = 0
    for road in intersection.ROADS:
        if road != request.location:
            reduction = min(15, intersection.sensors[road].vehicle_count)
            intersection.sensors[road].vehicle_count -= reduction
            cleared += reduction

    # Register in the emergency detector's active list
    if emergency_detector:
        _type_map = {
            "accident":  EmergencyType.ACCIDENT,
            "ambulance": EmergencyType.AMBULANCE,
            "fire_truck":EmergencyType.FIRE_TRUCK,
        }
        etype = _type_map.get(request.type, EmergencyType.AMBULANCE)
        emergency_detector.active_emergencies.append(EmergencyEvent(
            type=etype,
            location=request.location,
            priority=request.priority,
            timestamp=datetime.now(),
            description=f"MANUAL: {request.type} at {request.location}",
            duration=config.EMERGENCY_PRIORITY_DURATION,
            active=True,
        ))

    # Schedule automatic reset after the priority window expires
    asyncio.create_task(_reset_after_emergency(axis, request.location))

    return {
        "status":   "acknowledged",
        "action":   f"GREEN on {request.location} axis. {cleared} vehicles cleared.",
        "axis":     axis,
        "duration": config.EMERGENCY_PRIORITY_DURATION,
    }


async def _reset_after_emergency(axis: str, location: str):
    """Return the intersection to normal after the emergency window."""
    await asyncio.sleep(config.EMERGENCY_PRIORITY_DURATION)
    if intersection.current_green == axis:
        intersection.current_green = None
        intersection.state = TrafficLightState.RED
        if emergency_detector:
            emergency_detector.active_emergencies = [
                e for e in emergency_detector.active_emergencies
                if e.location != location or not e.active
            ]


@router.get("/emergencies")
async def get_emergency_log(limit: int = 20):
    """Return the most recent emergency events."""
    if not emergency_detector:
        return {"emergencies": [], "weather_condition": "clear"}

    emergencies = emergency_detector.get_emergency_log(limit)
    return {
        "emergencies": [
            {
                "type":        e.type.value,
                "location":    e.location,
                "priority":    e.priority,
                "description": e.description,
                "timestamp":   e.timestamp.isoformat(),
                "active":      e.active,
            }
            for e in emergencies
        ],
        "weather_condition": emergency_detector.weather_conditions,
    }
