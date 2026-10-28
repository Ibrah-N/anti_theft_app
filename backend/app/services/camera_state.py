# app/services/camera_state.py
#
# The last camera state each vehicle's firmware reported over MQTT
# (sg/<device_id>/camera/state). Kept in memory only: it is a live view of
# "what is the camera doing right now", not history. After a server restart it
# is empty until the camera next reports (the camera should also re-send its
# state whenever it (re)connects to MQTT).

from datetime import datetime, timezone

VALID_STATES = {"idle", "recording", "uploading", "streaming"}

_last: dict[int, dict] = {}


def set_state(vehicle_id: int, data: dict) -> dict | None:
    """Validate and store a camera report. Returns the cleaned dict, or None if invalid."""
    state = data.get("state")
    if state not in VALID_STATES:
        return None

    clean = {
        "state":      state,
        "clip_id":    _short(data.get("clip_id"), 64),
        "reason":     _short(data.get("reason"), 100),
        "elapsed_s":  _num(data.get("elapsed_s")),
        "segments_uploaded": _int(data.get("segments_uploaded")),
        "segments_total":    _int(data.get("segments_total")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _last[vehicle_id] = clean
    return clean


def get_state(vehicle_id: int) -> dict | None:
    return _last.get(vehicle_id)


def clear(vehicle_id: int):
    _last.pop(vehicle_id, None)


def _short(v, n):
    return str(v)[:n] if v is not None else None

def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

def _int(v):
    return int(v) if isinstance(v, int) and not isinstance(v, bool) else None