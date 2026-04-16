"""
Layer 5 - API: WebSocket handler
Pushes a state snapshot to every connected browser client every second.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .dependencies import simulation_manager, build_state_snapshot

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            if simulation_manager.running:
                state = await build_state_snapshot(save_to_db=False)
                await websocket.send_json(state)
            else:
                await websocket.send_json({"simulation_stopped": True})

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
