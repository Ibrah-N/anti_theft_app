# app/schemas/camera_media.py

from datetime import datetime
from pydantic import BaseModel

from app.models.camera_media import CameraMediaType


class CameraMediaResponse(BaseModel):
    id:               int
    sequence_number:  int
    media_type:       CameraMediaType
    file_size_bytes:  int
    duration_seconds: float | None
    created_at:       datetime

    model_config = {"from_attributes": True}


class CameraMediaListResponse(BaseModel):
    total: int
    items: list[CameraMediaResponse]