"""Uploader daemon entrypoint, launched with ``python -m scripts.worker``."""

import argparse
import asyncio
import logging
import signal
from typing import cast

from dotenv import load_dotenv

from uploader.application.cleanup_service import FinalizedStreamCleanupService
from uploader.application.playlist_reader import PlaylistReader
from uploader.application.polling import PollingWorker
from uploader.application.upload_service import StreamUploadService
from uploader.infrastructure.logging import configure_logging
from uploader.infrastructure.metrics import UploaderMetrics
from uploader.infrastructure.s3_client import S3ObjectStorage
from uploader.infrastructure.state_store import SqliteStateRepository
from uploader.specs.constants import LOGGER_WORKER
from uploader.specs.contracts import MetricsContract
from uploader.specs.settings import Settings

logger = logging.getLogger(LOGGER_WORKER)


def main() -> None:
    load_dotenv()
    """Configure the process and run the uploader until it receives a signal."""
    argparse.ArgumentParser(description="Run the HLS uploader daemon").parse_args()
    configure_logging()
    asyncio.run(run_daemon(Settings.from_environment()))


async def run_daemon(settings: Settings) -> None:
    """Create concrete adapters and inject them into application services."""
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    installed_signals = _install_shutdown_handlers(loop, stop_event)
    metrics_adapter = UploaderMetrics()
    metrics_adapter.start_server(settings.metrics_port)
    metrics = cast(MetricsContract, metrics_adapter)
    state = SqliteStateRepository(settings.state_db_path)
    try:
        async with S3ObjectStorage(
            endpoint_url=settings.s3_endpoint_url,
            bucket=settings.s3_bucket,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
        ) as storage:
            uploader = StreamUploadService(
                storage=storage,
                state=state,
                metrics=metrics,
                playlist_reader=PlaylistReader(),
                max_recording_seconds=settings.max_recording_seconds,
                last_segment_stable_seconds=settings.last_segment_stable_seconds,
                upload_concurrency=settings.upload_concurrency,
            )
            cleanup = FinalizedStreamCleanupService(
                state=state,
                metrics=metrics,
                retention_seconds=settings.playlist_retention_seconds,
            )
            await PollingWorker(
                settings=settings,
                state=state,
                metrics=metrics,
                uploader=uploader,
                cleanup=cleanup,
            ).run_forever(stop_event)
    finally:
        for shutdown_signal in installed_signals:
            loop.remove_signal_handler(shutdown_signal)
        state.close()


def _install_shutdown_handlers(
    loop: asyncio.AbstractEventLoop, stop_event: asyncio.Event
) -> tuple[signal.Signals, ...]:
    """Request a cooperative shutdown on container and interactive termination signals."""
    installed_signals: list[signal.Signals] = []
    for shutdown_signal in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(shutdown_signal, _request_shutdown, stop_event, shutdown_signal)
        except NotImplementedError:
            # Windows event loops do not support add_signal_handler. The
            # platform's default signal handling remains the safe fallback.
            continue
        installed_signals.append(shutdown_signal)
    return tuple(installed_signals)


def _request_shutdown(stop_event: asyncio.Event, shutdown_signal: signal.Signals) -> None:
    """Stop scheduling new work while allowing the current poll cycle to finish."""
    if stop_event.is_set():
        return
    logger.info("graceful shutdown requested", extra={"signal": shutdown_signal.name})
    stop_event.set()


if __name__ == "__main__":
    main()
