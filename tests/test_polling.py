import asyncio
import logging
from pathlib import Path

from pytest import LogCaptureFixture

from uploader.application.polling import PollingWorker
from uploader.specs.settings import Settings


class FakeMetric:
    def labels(self, *_: str) -> FakeMetric:
        return self

    def inc(self) -> None:
        pass

    def set(self, _: int | float) -> None:
        pass


class FakeMetrics:
    def __init__(self) -> None:
        self.stream_processing_errors = FakeMetric()
        self.streams = FakeMetric()
        self.pending_segments = FakeMetric()
        self.oldest_pending_seconds = FakeMetric()


class FakeState:
    def finalized_stream_ids(self) -> set[str]:
        return set()

    def expired_finalized_stream_ids(self, *, before: float) -> set[str]:
        return set()


class FakeUploader:
    def __init__(self) -> None:
        self.processed: list[str] = []

    async def publish_stream(self, stream_dir: Path) -> None:
        self.processed.append(stream_dir.name)
        if stream_dir.name == "broken-camera":
            raise RuntimeError("simulated failure")


class FakeCleanup:
    def cleanup_stream(self, stream_dir: Path, *, now: float) -> None:
        raise AssertionError(f"unexpected cleanup for {stream_dir} at {now}")


def test_polling_logs_one_failure_and_continues_with_other_streams(
    tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    (tmp_path / "broken-camera").mkdir()
    (tmp_path / "healthy-camera").mkdir()
    settings = Settings(
        recordings_dir=tmp_path,
        state_db_path=tmp_path / "state.sqlite3",
        s3_endpoint_url="http://s3.invalid",
        s3_bucket="video",
        s3_access_key_id="key",
        s3_secret_access_key="secret",
        poll_interval_seconds=1,
        last_segment_stable_seconds=1,
        max_recording_seconds=1,
        playlist_retention_seconds=1,
        metrics_port=0,
        upload_concurrency=1,
    )
    uploader = FakeUploader()
    worker = PollingWorker(
        settings=settings,
        state=FakeState(),  # type: ignore[arg-type]
        metrics=FakeMetrics(),  # type: ignore[arg-type]
        uploader=uploader,
        cleanup=FakeCleanup(),
    )

    with caplog.at_level(logging.ERROR, logger="uploader.daemon"):
        asyncio.run(worker.process_once())

    assert uploader.processed == ["broken-camera", "healthy-camera"]
    assert "stream publication failed" in caplog.text
    assert getattr(caplog.records[0], "task_name") == "publish:broken-camera"


def test_polling_stops_without_starting_a_new_cycle_when_shutdown_requested(
    tmp_path: Path,
) -> None:
    settings = Settings(
        recordings_dir=tmp_path,
        state_db_path=tmp_path / "state.sqlite3",
        s3_endpoint_url="http://s3.invalid",
        s3_bucket="video",
        s3_access_key_id="key",
        s3_secret_access_key="secret",
        poll_interval_seconds=1,
        last_segment_stable_seconds=1,
        max_recording_seconds=1,
        playlist_retention_seconds=1,
        metrics_port=0,
        upload_concurrency=1,
    )
    uploader = FakeUploader()
    worker = PollingWorker(
        settings=settings,
        state=FakeState(),  # type: ignore[arg-type]
        metrics=FakeMetrics(),  # type: ignore[arg-type]
        uploader=uploader,
        cleanup=FakeCleanup(),
    )
    stop_event = asyncio.Event()
    stop_event.set()

    asyncio.run(worker.run_forever(stop_event))

    assert uploader.processed == []
