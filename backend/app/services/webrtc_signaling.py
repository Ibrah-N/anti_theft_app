# app/services/webrtc_signaling.py

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory session registry — one active camera session per vehicle at a
# time (matches the hardware's single-stream limit, and keeps this simple:
# no cross-process state needed since MQTT + WebSocket both live in this
# one backend process).
_active_sessions: dict[int, dict] = {}
# vehicle_id -> {"call_id": str, "started_at": datetime}


def start_session(vehicle_id: int) -> str:
    """Begin a new camera session for this vehicle, replacing any previous one."""
    call_id = str(uuid.uuid4())
    _active_sessions[vehicle_id] = {
        "call_id":    call_id,
        "started_at": datetime.now(timezone.utc),
    }
    logger.info(f"WebRTC session started — vehicle {vehicle_id} call_id={call_id}")
    return call_id


def end_session(vehicle_id: int):
    if vehicle_id in _active_sessions:
        logger.info(
            f"WebRTC session ended — vehicle {vehicle_id} "
            f"call_id={_active_sessions[vehicle_id]['call_id']}"
        )
        del _active_sessions[vehicle_id]


def get_call_id(vehicle_id: int) -> Optional[str]:
    session = _active_sessions.get(vehicle_id)
    return session["call_id"] if session else None


def is_valid_call(vehicle_id: int, call_id: str) -> bool:
    """
    Guards against stale signaling messages from a session that has since
    ended or been superseded — same spirit as the command-timestamp expiry
    used for vehicle controls, applied here to WebRTC's own session concept.
    """
    current = get_call_id(vehicle_id)
    return current is not None and current == call_id