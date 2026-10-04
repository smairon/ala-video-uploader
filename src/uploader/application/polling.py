"""Application scheduler that coordinates stream publication and retention cleanup."""

import asyncio
import logging
import time
from pathlib import Path

from uploader.specs.constants import (
    LOGGER_DAEMON,
    METRIC_OPERATION_CLEANUP,
    METRIC_OPERATION_PUBLISH,
    METRIC_STREAM_STATE_ACTIVE,
    METRIC_STREAM_STATE_FINALIZED,
    SEGMENT_FILE_GLOB,
    TASK_NAME_PUBLISH_PREFIX,
)
from uploader.specs.contracts import (
    MetricsContract,
    StateStoreContract,
    StreamCleanerContract,
    StreamUploaderContract,
)
from uploader.specs.settings import Settings

logger = logging.getLogger(LOGGER_DAEMON)


class PollingWorker:
    """Schedules active streams and retention cleanup in independent passes."""

    def __init__(
        self,
        *,
        settings: Settings,
        state: StateStoreContract,
        metrics: MetricsContract,
        uploader: StreamUploaderContract,
        cleanup: StreamCleanerContract,
    ) -> None:
        self._settings = settings
        self._state = state
        self._metrics = metrics
        self._uploader = uploader
        self._cleanup = cleanup

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        """Poll until shutdown is requested, completing any active cycle first."""
        while not stop_event.is_set():
            await self.process_once()
            if stop_event.is_set():
                break
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=self._settings.poll_interval_seconds
                )
            except TimeoutError:
                # The poll interval elapsed normally; start the next snapshot.
                continue

    async def process_once(self) -> None:
        stream_directories = [
            path for path in self._settings.recordings_dir.iterdir() if path.is_dir()
        ]
        now = time.time()
        finalized_ids = self._state.finalized_stream_ids()
        finalized_directories = [path for path in stream_directories if path.name in finalized_ids]
        active_directories = [path for path in stream_directories if path.name not in finalized_ids]
        expired_ids = self._state.expired_finalized_stream_ids(
            before=now - self._settings.playlist_retention_seconds
        )
        self._update_metrics(active_directories, finalized_directories)
        tasks_by_stream_id = {
            stream_dir.name: asyncio.create_task(
                self._uploader.publish_stream(stream_dir),
                name=f"{TASK_NAME_PUBLISH_PREFIX}{stream_dir.name}",
            )
            for stream_dir in active_directories
        }
        results = await asyncio.gather(*tasks_by_stream_id.values(), return_exceptions=True)
        for (stream_id, task), result in zip(tasks_by_stream_id.items(), results, strict=True):
            self._log_publish_failure(stream_id, task, result)
        for stream_dir in finalized_directories:
            if stream_dir.name in expired_ids:
                self._cleanup_safely(stream_dir, now)

    def _log_publish_failure(
        self, stream_id: str, task: asyncio.Task[None], result: object
    ) -> None:
        if not isinstance(result, BaseException):
            return
        if isinstance(result, asyncio.CancelledError):
            raise result
        self._metrics.stream_processing_errors.labels(METRIC_OPERATION_PUBLISH).inc()
        logger.error(
            "stream publication failed",
            exc_info=(type(result), result, result.__traceback__),
            extra={"stream_id": stream_id, "task_name": task.get_name()},
        )

    def _cleanup_safely(self, stream_dir: Path, now: float) -> None:
        try:
            self._cleanup.cleanup_stream(stream_dir, now=now)
        except Exception:
            self._metrics.stream_processing_errors.labels(METRIC_OPERATION_CLEANUP).inc()
            logger.exception(
                "finalized stream cleanup failed", extra={"stream_id": stream_dir.name}
            )

    def _update_metrics(
        self, active_directories: list[Path], finalized_directories: list[Path]
    ) -> None:
        self._metrics.streams.labels(METRIC_STREAM_STATE_ACTIVE).set(len(active_directories))
        self._metrics.streams.labels(METRIC_STREAM_STATE_FINALIZED).set(len(finalized_directories))
        pending_paths = [
            segment
            for directory in active_directories
            for segment in directory.glob(SEGMENT_FILE_GLOB)
        ]
        self._metrics.pending_segments.set(len(pending_paths))
        oldest_mtime = min((segment.stat().st_mtime for segment in pending_paths), default=None)
        self._metrics.oldest_pending_seconds.set(
            0 if oldest_mtime is None else max(0, time.time() - oldest_mtime)
        )
