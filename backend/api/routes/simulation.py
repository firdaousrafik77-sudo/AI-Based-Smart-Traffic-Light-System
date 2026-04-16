"""
Layer 5 - API Routes: Simulation control + sensor update + state
"""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..dependencies import simulation_manager, intersection, build_state_snapshot

router = APIRouter(prefix="/api", tags=["simulation"])
logger = logging.getLogger(__name__)


# ---- Pydantic request model ------------------------------------------

class SensorData(BaseModel):
    """Body for POST /api/sensor/update"""
    north: int
    south: int
    east:  int
    west:  int
    timestamp: Optional[str] = None


# ---- Endpoints -------------------------------------------------------

@router.post("/simulation/start")
async def start_simulation():
    started = await simulation_manager.start()
    if not started:
        return {"status": "already_running",
                "message": "Simulation is already active"}
    return {"status": "started",
            "message": "Smart traffic control system activated"}


@router.post("/simulation/stop")
async def stop_simulation():
    await simulation_manager.stop()
    return {"status": "stopped", "message": "Simulation stopped"}


@router.get("/state")
async def get_state():
    """Current intersection snapshot + ML predictions."""
    return await build_state_snapshot(save_to_db=True)


@router.post("/sensor/update")
async def update_sensor_data(data: SensorData):
    """Accept live sensor readings from external IoT devices."""
    traffic_data = {
        "North": data.north,
        "South": data.south,
        "East":  data.east,
        "West":  data.west,
    }
    await intersection.update_sensors(traffic_data)
    return {"status": "updated", "data": traffic_data}
