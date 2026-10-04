import asyncio
from pathlib import Path

from uploader.application.cleanup_service import FinalizedStreamCleanupService
from uploader.application.playlist_reader import PlaylistReader
from uploader.application.upload_service import StreamUploadService
from uploader.infrastructure.state_store import SqliteStateRepository


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, str] = {}
        self.uploaded_keys: list[str] = []

    async def upload_file(
        self, *, key: str, path: Path, content_type: str, cache_control: str
    ) -> str:
        self.uploaded_keys.append(key)
        self.objects[key] = path.read_text(encoding="utf-8")
        return '"test-etag"'


class FakeMetric:
    """Captures metric labels without registering global Prometheus collectors."""

    def __init__(self) -> None:
        self.labels_used: list[str] = []
        self.increment_count = 0

    def labels(self, *labels: str) -> FakeMetric:
        self.labels_used.extend(labels)
        return self

    def inc(self, _: float = 1) -> None:
        self.increment_count += 1

    def observe(self, _: float) -> None:
        pass


class CleanupMetrics:
    """Provides exactly the metric surface used by finalized-stream cleanup."""

    def __init__(self) -> None:
        self.deleted_files = FakeMetric()


class PublisherMetrics:
    """Provides the metrics surface used by upload and playlist publication tests."""

    def __init__(self) -> None:
        self.uploads = FakeMetric()
        self.upload_duration = FakeMetric()
        self.uploaded_bytes = FakeMetric()
        self.deleted_files = FakeMetric()


def test_publishes_only_closed_segments_before_playlist(tmp_path: Path) -> None:
    stream_dir = tmp_path / "camera-1"
    stream_dir.mkdir()
    first = "2020-01-01T00:00:00.000001.ts"
    second = "2020-01-01T00:00:10.000002.ts"
    current = "2020-01-01T00:00:20.000003.ts"
    for name in (first, second, current):
        (stream_dir / name).write_text(name, encoding="utf-8")
    (stream_dir / "playlist.m3u8").write_text(
        "#EXTM3U\n" + "".join(f"#EXTINF:10.0,\n{name}\n" for name in (first, second, current)),
        encoding="utf-8",
    )
    storage = FakeStorage()
    state = SqliteStateRepository(tmp_path / "state.sqlite3")
    publisher = StreamUploadService(
        storage=storage,
        state=state,
        metrics=PublisherMetrics(),  # type: ignore[arg-type]
        playlist_reader=PlaylistReader(),
        max_recording_seconds=10**12,
        last_segment_stable_seconds=10**12,
        upload_concurrency=2,
    )

    asyncio.run(publisher.publish_stream(stream_dir))

    assert set(storage.objects) == {
        f"streams/camera-1/{first}",
        f"streams/camera-1/{second}",
        "streams/camera-1/playlist.m3u8",
    }
    published_playlist = storage.objects["streams/camera-1/playlist.m3u8"]
    assert first in published_playlist
    assert second in published_playlist
    assert current not in published_playlist
    assert not (stream_dir / first).exists()
    assert not (stream_dir / second).exists()
    assert (stream_dir / current).exists()

    # The recorder's VOD playlist retains old URI lines after local cleanup.
    # A subsequent poll must use SQLite metadata instead of stat'ing those paths.
    asyncio.run(publisher.publish_stream(stream_dir))
    assert current not in storage.objects["streams/camera-1/playlist.m3u8"]


def test_uploads_stable_last_segment_and_does_not_republish_same_playlist(tmp_path: Path) -> None:
    stream_dir = tmp_path / "camera-1"
    stream_dir.mkdir()
    first = "2020-01-01T00:00:00.000001.ts"
    last = "2020-01-01T00:00:10.000002.ts"
    for name in (first, last):
        (stream_dir / name).write_text(name, encoding="utf-8")
    (stream_dir / "playlist.m3u8").write_text(
        "#EXTM3U\n" + "".join(f"#EXTINF:10.0,\n{name}\n" for name in (first, last)),
        encoding="utf-8",
    )
    storage = FakeStorage()
    state = SqliteStateRepository(tmp_path / "state.sqlite3")
    last_path = stream_dir / last
    last_stat = last_path.stat()
    state.observe_segment(
        stream_id="camera-1",
        uri=last,
        size_bytes=last_stat.st_size,
        modified_at=last_stat.st_mtime,
        observed_at=0,
    )
    publisher = StreamUploadService(
        storage=storage,
        state=state,
        metrics=PublisherMetrics(),  # type: ignore[arg-type]
        playlist_reader=PlaylistReader(),
        max_recording_seconds=10**12,
        last_segment_stable_seconds=1,
        upload_concurrency=2,
    )

    asyncio.run(publisher.publish_stream(stream_dir))
    asyncio.run(publisher.publish_stream(stream_dir))

    assert set(storage.objects) == {
        f"streams/camera-1/{first}",
        f"streams/camera-1/{last}",
        "streams/camera-1/playlist.m3u8",
    }
    assert storage.uploaded_keys.count("streams/camera-1/playlist.m3u8") == 1
    assert last in storage.objects["streams/camera-1/playlist.m3u8"]
    assert not last_path.exists()


def test_cleanup_finalized_stream_removes_retained_playlist_and_empty_directory(
    tmp_path: Path,
) -> None:
    stream_dir = tmp_path / "camera-1"
    stream_dir.mkdir()
    (stream_dir / "playlist.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
    state = SqliteStateRepository(tmp_path / "state.sqlite3")
    state.register_stream(stream_id="camera-1", first_segment_at=1.0, playlist_seen_at=10.0)
    state.mark_finalized(stream_id="camera-1", finalized_at=20.0)
    metrics = CleanupMetrics()
    cleanup = FinalizedStreamCleanupService(
        state=state,
        metrics=metrics,  # type: ignore[arg-type]
        retention_seconds=100,
    )

    cleanup.cleanup_stream(stream_dir, now=110.0)

    assert not stream_dir.exists()
    assert metrics.deleted_files.labels_used == ["playlist"]
    assert metrics.deleted_files.increment_count == 1
