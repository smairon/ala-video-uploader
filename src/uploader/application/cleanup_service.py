"""Application service for retained local artifacts of finalized streams."""

import logging
from pathlib import Path

from uploader.specs.constants import LOGGER_CLEANUP, METRIC_OBJECT_TYPE_PLAYLIST, PLAYLIST_FILENAME
from uploader.specs.contracts import MetricsContract, StateStoreContract

logger = logging.getLogger(LOGGER_CLEANUP)


class FinalizedStreamCleanupService:
    """Removes local finalized-stream files only after the configured retention period."""

    def __init__(
        self, *, state: StateStoreContract, metrics: MetricsContract, retention_seconds: int
    ) -> None:
        self._state = state
        self._metrics = metrics
        self._retention_seconds = retention_seconds

    def cleanup_stream(self, stream_dir: Path, *, now: float) -> None:
        """Delete a retained playlist and then its directory only when empty."""
        stream_id = stream_dir.name
        try:
            _, playlist_seen_at, finalized_at = self._state.stream_metadata(stream_id)
        except KeyError:
            return
        if finalized_at is None or now < playlist_seen_at + self._retention_seconds:
            return
        playlist_path = stream_dir / PLAYLIST_FILENAME
        if playlist_path.exists():
            playlist_path.unlink()
            self._metrics.deleted_files.labels(METRIC_OBJECT_TYPE_PLAYLIST).inc()
            logger.info("expired local playlist deleted", extra={"stream_id": stream_id})
        try:
            stream_dir.rmdir()
        except OSError:
            logger.debug("completed stream directory is not empty", extra={"stream_id": stream_id})
        else:
            logger.info("completed stream directory deleted", extra={"stream_id": stream_id})
