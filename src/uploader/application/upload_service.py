"""Application service that publishes one stream without exposing partial HLS state."""

import asyncio
import hashlib
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from uploader.specs.constants import (
    LOGGER_PUBLISHER,
    METRIC_OBJECT_TYPE_PLAYLIST,
    METRIC_OBJECT_TYPE_SEGMENT,
    METRIC_OUTCOME_ERROR,
    METRIC_OUTCOME_SUCCESS,
    PLAYLIST_CONTENT_TYPE,
    PLAYLIST_FILENAME,
    PUBLISHED_PLAYLIST_FILENAME,
    S3_PLAYLIST_CACHE_CONTROL,
    S3_SEGMENT_CACHE_CONTROL,
    S3_STREAMS_PREFIX,
    SEGMENT_CONTENT_TYPE,
    TEXT_ENCODING_UTF8,
)
from uploader.specs.contracts import (
    MetricsContract,
    ObjectStorageContract,
    PlaylistCodecContract,
    StateStoreContract,
)
from uploader.specs.models import PlaylistSegment

logger = logging.getLogger(LOGGER_PUBLISHER)


class StreamUploadService:
    """Publishes complete segments first, then the playlist that references them."""

    def __init__(
        self,
        *,
        storage: ObjectStorageContract,
        state: StateStoreContract,
        metrics: MetricsContract,
        playlist_reader: PlaylistCodecContract,
        max_recording_seconds: int,
        last_segment_stable_seconds: float,
        upload_concurrency: int,
    ) -> None:
        self._storage = storage
        self._state = state
        self._metrics = metrics
        self._playlist_reader = playlist_reader
        self._max_recording_seconds = max_recording_seconds
        self._last_segment_stable_seconds = last_segment_stable_seconds
        self._upload_semaphore = asyncio.Semaphore(upload_concurrency)

    async def publish_stream(self, stream_dir: Path) -> None:
        """Synchronize a recorder directory with its deterministic S3 prefix."""
        playlist_path = stream_dir / PLAYLIST_FILENAME
        if not playlist_path.is_file():
            logger.debug("stream has no playlist yet", extra={"stream_id": stream_dir.name})
            return
        playlist = self._playlist_reader.parse(playlist_path.read_text(encoding=TEXT_ENCODING_UTF8))
        if not playlist.segments:
            return

        now = time.time()
        stream_id = stream_dir.name
        try:
            started_at, _, finalized_at = self._state.stream_metadata(stream_id)
        except KeyError:
            self._state.register_stream(
                stream_id=stream_id,
                first_segment_at=self._segment_timestamp(playlist.segments[0].uri, stream_dir),
                playlist_seen_at=playlist_path.stat().st_ctime,
            )
            started_at, _, finalized_at = self._state.stream_metadata(stream_id)
        if finalized_at is not None:
            return

        finalization_due = now >= started_at + self._max_recording_seconds
        ready_uris = self._ready_uris(
            stream_id=stream_id,
            segments=playlist.segments,
            stream_dir=stream_dir,
            observed_at=now,
            finalization_due=finalization_due,
        )
        await asyncio.gather(
            *(self._upload_segment(stream_id, stream_dir / uri, uri) for uri in ready_uris)
        )

        published_uris = self._state.uploaded_uris(stream_id)
        is_final = finalization_due and all(
            segment.uri in published_uris for segment in playlist.segments
        )
        rendered = self._playlist_reader.render(playlist, published_uris, finalized=is_final)
        if published_uris:
            playlist_uploaded = await self._upload_playlist(stream_id, rendered, playlist_path)
        else:
            playlist_uploaded = False
        if is_final and playlist_uploaded:
            self._state.mark_finalized(stream_id=stream_id, finalized_at=now)
            logger.info("stream finalized", extra={"stream_id": stream_id})

    def _ready_uris(
        self,
        *,
        stream_id: str,
        segments: tuple[PlaylistSegment, ...],
        stream_dir: Path,
        observed_at: float,
        finalization_due: bool,
    ) -> list[str]:
        """Return closed segments and a stable current segment when it stopped changing."""
        ready_uris = [
            segment.uri for segment in segments[:-1] if (stream_dir / segment.uri).is_file()
        ]
        last_segment = segments[-1]
        last_path = stream_dir / last_segment.uri
        if not last_path.is_file():
            return ready_uris

        if finalization_due:
            ready_uris.append(last_segment.uri)
            return ready_uris

        last_stat = last_path.stat()
        stable_since = self._state.observe_segment(
            stream_id=stream_id,
            uri=last_segment.uri,
            size_bytes=last_stat.st_size,
            modified_at=last_stat.st_mtime,
            observed_at=observed_at,
        )
        if observed_at - stable_since >= self._last_segment_stable_seconds:
            ready_uris.append(last_segment.uri)
        return ready_uris

    async def _upload_segment(self, stream_id: str, path: Path, uri: str) -> None:
        """Upload and journal a segment before unlinking its immutable local copy."""
        if uri in self._state.uploaded_uris(stream_id):
            path.unlink(missing_ok=True)
            return
        async with self._upload_semaphore:
            started = time.monotonic()
            try:
                etag = await self._storage.upload_file(
                    key=f"{S3_STREAMS_PREFIX}/{stream_id}/{uri}",
                    path=path,
                    content_type=SEGMENT_CONTENT_TYPE,
                    cache_control=S3_SEGMENT_CACHE_CONTROL,
                )
            except Exception:
                self._metrics.uploads.labels(METRIC_OBJECT_TYPE_SEGMENT, METRIC_OUTCOME_ERROR).inc()
                logger.exception(
                    "segment upload failed", extra={"stream_id": stream_id, "uri": uri}
                )
                return
            self._metrics.upload_duration.labels(METRIC_OBJECT_TYPE_SEGMENT).observe(
                time.monotonic() - started
            )
            self._metrics.uploads.labels(METRIC_OBJECT_TYPE_SEGMENT, METRIC_OUTCOME_SUCCESS).inc()
            self._metrics.uploaded_bytes.inc(path.stat().st_size)
            self._state.mark_uploaded(
                stream_id=stream_id, uri=uri, etag=etag, uploaded_at=time.time()
            )
            path.unlink(missing_ok=True)
            self._metrics.deleted_files.labels(METRIC_OBJECT_TYPE_SEGMENT).inc()
            logger.info(
                "segment uploaded", extra={"stream_id": stream_id, "uri": uri, "etag": etag}
            )

    async def _upload_playlist(self, stream_id: str, rendered: str, playlist_path: Path) -> bool:
        """Publish changed rendered content without modifying the recorder's playlist."""
        content_hash = hashlib.sha256(rendered.encode(TEXT_ENCODING_UTF8)).hexdigest()
        if self._state.published_playlist_hash(stream_id) == content_hash:
            logger.debug("playlist unchanged", extra={"stream_id": stream_id})
            return True
        published_path = playlist_path.with_name(PUBLISHED_PLAYLIST_FILENAME)
        published_path.write_text(rendered, encoding=TEXT_ENCODING_UTF8)
        try:
            async with self._upload_semaphore:
                await self._storage.upload_file(
                    key=f"{S3_STREAMS_PREFIX}/{stream_id}/{PLAYLIST_FILENAME}",
                    path=published_path,
                    content_type=PLAYLIST_CONTENT_TYPE,
                    cache_control=S3_PLAYLIST_CACHE_CONTROL,
                )
                self._state.mark_playlist_published(
                    stream_id=stream_id,
                    content_hash=content_hash,
                    published_at=time.time(),
                )
            self._metrics.uploads.labels(METRIC_OBJECT_TYPE_PLAYLIST, METRIC_OUTCOME_SUCCESS).inc()
            logger.info("playlist published", extra={"stream_id": stream_id})
            return True
        except Exception:
            self._metrics.uploads.labels(METRIC_OBJECT_TYPE_PLAYLIST, METRIC_OUTCOME_ERROR).inc()
            logger.exception("playlist upload failed", extra={"stream_id": stream_id})
            return False
        finally:
            published_path.unlink(missing_ok=True)

    @staticmethod
    def _segment_timestamp(uri: str, stream_dir: Path) -> float:
        """Use the segment timestamp, falling back to the recorder's file metadata."""
        try:
            return datetime.fromisoformat(Path(uri).stem).replace(tzinfo=UTC).timestamp()
        except ValueError:
            return (stream_dir / uri).stat().st_ctime
