# app/services/websocket_service.py

import json
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # vehicle_id → list of connected WebSocket clients
        self._connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, vehicle_id: int, websocket: WebSocket):
        await websocket.accept()
        if vehicle_id not in self._connections:
            self._connections[vehicle_id] = []
        self._connections[vehicle_id].append(websocket)
        logger.info(
            f"WebSocket connected — vehicle {vehicle_id} "
            f"({len(self._connections[vehicle_id])} clients)"
        )

    def disconnect(self, vehicle_id: int, websocket: WebSocket):
        if vehicle_id in self._connections:
            self._connections[vehicle_id].discard(websocket)
            logger.info(f"WebSocket disconnected — vehicle {vehicle_id}")

    async def broadcast(self, vehicle_id: int, message: dict):
        """Push a message to all clients watching this vehicle."""
        clients = self._connections.get(vehicle_id, [])
        if not clients:
            return

        payload  = json.dumps(message)
        dead     = []

        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        # Clean up disconnected clients
        for ws in dead:
            self._connections[vehicle_id].remove(ws)


# ── Singleton ─────────────────────────────────────────────────────────────────
ws_manager = WebSocketManager()