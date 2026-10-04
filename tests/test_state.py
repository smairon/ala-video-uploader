from pathlib import Path

import pytest

from uploader.infrastructure.state_store import SqliteStateRepository


def test_stream_registration_keeps_the_first_seen_timestamps(tmp_path: Path) -> None:
    repository = SqliteStateRepository(tmp_path / "state.sqlite3")

    repository.register_stream(stream_id="camera-1", first_segment_at=100.0, playlist_seen_at=101.0)
    repository.register_stream(stream_id="camera-1", first_segment_at=200.0, playlist_seen_at=201.0)

    assert repository.stream_metadata("camera-1") == (100.0, 101.0, None)
    repository.close()


def test_uploaded_object_is_idempotent_and_updates_its_etag(tmp_path: Path) -> None:
    repository = SqliteStateRepository(tmp_path / "state.sqlite3")
    repository.register_stream(stream_id="camera-1", first_segment_at=100.0, playlist_seen_at=101.0)

    repository.mark_uploaded(
        stream_id="camera-1", uri="segment-1.ts", etag="old", uploaded_at=102.0
    )
    repository.mark_uploaded(
        stream_id="camera-1", uri="segment-1.ts", etag="new", uploaded_at=103.0
    )

    assert repository.uploaded_uris("camera-1") == {"segment-1.ts"}
    etag, uploaded_at = repository._connection.execute(
        "SELECT etag, uploaded_at FROM uploaded_objects WHERE stream_id = ? AND uri = ?",
        ("camera-1", "segment-1.ts"),
    ).fetchone()
    assert (etag, uploaded_at) == ("new", 103.0)
    repository.close()


def test_finalization_time_is_recorded_once(tmp_path: Path) -> None:
    repository = SqliteStateRepository(tmp_path / "state.sqlite3")
    repository.register_stream(stream_id="camera-1", first_segment_at=100.0, playlist_seen_at=101.0)

    repository.mark_finalized(stream_id="camera-1", finalized_at=200.0)
    repository.mark_finalized(stream_id="camera-1", finalized_at=300.0)

    assert repository.stream_metadata("camera-1") == (100.0, 101.0, 200.0)
    assert repository.finalized_stream_ids() == {"camera-1"}
    assert repository.expired_finalized_stream_ids(before=100.0) == set()
    assert repository.expired_finalized_stream_ids(before=101.0) == {"camera-1"}
    repository.close()


def test_unknown_stream_metadata_raises_key_error(tmp_path: Path) -> None:
    repository = SqliteStateRepository(tmp_path / "state.sqlite3")

    with pytest.raises(KeyError, match="camera-unknown"):
        repository.stream_metadata("camera-unknown")

    repository.close()
