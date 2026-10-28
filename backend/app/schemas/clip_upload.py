# app/schemas/clip_upload.py

from datetime import datetime
from pydantic import BaseModel, Field

from app.models.clip_upload import ClipUploadStatus
from app.schemas.camera_media import CameraMediaResponse
from app.services.clip_storage import CLIP_ID_PATTERN


class DeviceKeyResponse(BaseModel):
    device_id:  str
    device_key: str
    note:       str = "Save this key now — it cannot be shown again. Creating a new one disables this one."


class ClipStartRequest(BaseModel):
    client_clip_id: str = Field(pattern=CLIP_ID_PATTERN)   # camera-made unique id, e.g. a UUID
    trigger_reason: str | None = Field(default=None, max_length=100)
    recorded_at:    datetime | None = None                 # when the camera started recording


class ClipFinishRequest(BaseModel):
    total_segments:   int = Field(ge=1)
    duration_seconds: float | None = Field(default=None, ge=0)
    # If true, join whatever arrived even when some segments are missing
    # (e.g. the camera lost power and can never produce the rest).
    allow_partial:    bool = False


class ClipStatusResponse(BaseModel):
    client_clip_id:    str
    status:            ClipUploadStatus
    segments_received: list[int]          # indexes the server already has — resend only the others
    bytes_received:    int
    total_segments:    int | None = None
    media_id:          int | None = None  # set once the clip is in the gallery
    media:             CameraMediaResponse | None = None