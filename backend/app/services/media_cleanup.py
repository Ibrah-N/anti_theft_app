# app/services/media_cleanup.py

import os
import time
import logging
import threading
from datetime import datetime, timezone, timedelta

from app.core.database import SessionLocal
from app.models.camera_media import CameraMedia

logger = logging.getLogger(__name__)

MEDIA_RETENTION_DAYS      = 30
CLEANUP_INTERVAL_SECONDS  = 6 * 60 * 60  # every 6 hours


def delete_expired_media():
    """
    Delete camera_media rows — and their actual files on disk — once they're
    older than the retention window. Runs in its own DB session since it
    executes outside any request's lifecycle.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=MEDIA_RETENTION_DAYS)
    db = SessionLocal()
    try:
        expired = db.query(CameraMedia).filter(CameraMedia.created_at < cutoff).all()

        for media in expired:
            try:
                if os.path.exists(media.file_path):
                    os.remove(media.file_path)
            except OSError as e:
                logger.warning(f"Could not remove expired media file {media.file_path}: {e}")
            db.delete(media)

        if expired:
            db.commit()
            logger.info(
                f"Media cleanup — deleted {len(expired)} item(s) older than "
                f"{MEDIA_RETENTION_DAYS} days"
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Media cleanup failed: {e}")
    finally:
        db.close()


def _cleanup_loop():
    # Run once shortly after startup (catches anything that expired while
    # the server was down), then on a steady interval from then on.
    while True:
        delete_expired_media()
        time.sleep(CLEANUP_INTERVAL_SECONDS)


def start_cleanup_thread():
    thread = threading.Thread(target=_cleanup_loop, daemon=True, name="media-cleanup")
    thread.start()
    logger.info(
        f"Media cleanup thread started — retention={MEDIA_RETENTION_DAYS}d, "
        f"interval={CLEANUP_INTERVAL_SECONDS}s"
    )