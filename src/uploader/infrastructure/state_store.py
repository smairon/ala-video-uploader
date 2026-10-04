"""Durable SQLite persistence for stream lifecycle and S3 acknowledgements."""

import sqlite3
from pathlib import Path

from uploader.specs.constants import SQLITE_JOURNAL_MODE_WAL, SQLITE_SYNCHRONOUS_MODE_FULL


class SqliteStateRepository:
    """Stores confirmed objects and finalized stream lifecycle timestamps."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(f"PRAGMA journal_mode={SQLITE_JOURNAL_MODE_WAL}")
        self._connection.execute(f"PRAGMA synchronous={SQLITE_SYNCHRONOUS_MODE_FULL}")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS streams (
                stream_id TEXT PRIMARY KEY,
                first_segment_at REAL NOT NULL,
                playlist_seen_at REAL NOT NULL,
                finalized_at REAL
            );
            CREATE TABLE IF NOT EXISTS uploaded_objects (
                stream_id TEXT NOT NULL,
                uri TEXT NOT NULL,
                etag TEXT NOT NULL,
                uploaded_at REAL NOT NULL,
                PRIMARY KEY (stream_id, uri)
            );
            CREATE TABLE IF NOT EXISTS segment_observations (
                stream_id TEXT NOT NULL,
                uri TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_at REAL NOT NULL,
                stable_since REAL NOT NULL,
                PRIMARY KEY (stream_id, uri)
            );
            CREATE TABLE IF NOT EXISTS published_playlists (
                stream_id TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                published_at REAL NOT NULL
            );
            """
        )
        self._connection.commit()

    def register_stream(
        self, *, stream_id: str, first_segment_at: float, playlist_seen_at: float
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO streams(stream_id, first_segment_at, playlist_seen_at)
            VALUES (?, ?, ?)
            ON CONFLICT(stream_id) DO NOTHING
            """,
            (stream_id, first_segment_at, playlist_seen_at),
        )
        self._connection.commit()

    def uploaded_uris(self, stream_id: str) -> set[str]:
        rows = self._connection.execute(
            "SELECT uri FROM uploaded_objects WHERE stream_id = ?", (stream_id,)
        )
        return {str(row["uri"]) for row in rows}

    def mark_uploaded(self, *, stream_id: str, uri: str, etag: str, uploaded_at: float) -> None:
        self._connection.execute(
            """
            INSERT INTO uploaded_objects(stream_id, uri, etag, uploaded_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(stream_id, uri) DO UPDATE SET
                etag = excluded.etag,
                uploaded_at = excluded.uploaded_at
            """,
            (stream_id, uri, etag, uploaded_at),
        )
        self._connection.commit()

    def stream_metadata(self, stream_id: str) -> tuple[float, float, float | None]:
        row = self._connection.execute(
            "SELECT first_segment_at, playlist_seen_at, finalized_at "
            "FROM streams WHERE stream_id = ?",
            (stream_id,),
        ).fetchone()
        if row is None:
            raise KeyError(stream_id)
        return float(row["first_segment_at"]), float(row["playlist_seen_at"]), row["finalized_at"]

    def mark_finalized(self, *, stream_id: str, finalized_at: float) -> None:
        self._connection.execute(
            "UPDATE streams SET finalized_at = COALESCE(finalized_at, ?) WHERE stream_id = ?",
            (finalized_at, stream_id),
        )
        self._connection.commit()

    def finalized_stream_ids(self) -> set[str]:
        rows = self._connection.execute(
            "SELECT stream_id FROM streams WHERE finalized_at IS NOT NULL"
        )
        return {str(row["stream_id"]) for row in rows}

    def expired_finalized_stream_ids(self, *, before: float) -> set[str]:
        rows = self._connection.execute(
            "SELECT stream_id FROM streams "
            "WHERE finalized_at IS NOT NULL AND playlist_seen_at <= ?",
            (before,),
        )
        return {str(row["stream_id"]) for row in rows}

    def observe_segment(
        self,
        *,
        stream_id: str,
        uri: str,
        size_bytes: int,
        modified_at: float,
        observed_at: float,
    ) -> float:
        """Return when an unchanged segment fingerprint was first observed.

        The recorder can keep writing its last file. Persisting its size and
        mtime fingerprint lets a restarted uploader continue the same stability
        window instead of treating a partially written file as complete.
        """
        row = self._connection.execute(
            """
            SELECT size_bytes, modified_at, stable_since
            FROM segment_observations
            WHERE stream_id = ? AND uri = ?
            """,
            (stream_id, uri),
        ).fetchone()
        if (
            row is not None
            and row["size_bytes"] == size_bytes
            and row["modified_at"] == modified_at
        ):
            return float(row["stable_since"])
        self._connection.execute(
            """
            INSERT INTO segment_observations(stream_id, uri, size_bytes, modified_at, stable_since)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(stream_id, uri) DO UPDATE SET
                size_bytes = excluded.size_bytes,
                modified_at = excluded.modified_at,
                stable_since = excluded.stable_since
            """,
            (stream_id, uri, size_bytes, modified_at, observed_at),
        )
        self._connection.commit()
        return observed_at

    def published_playlist_hash(self, stream_id: str) -> str | None:
        """Return the exact rendered playlist fingerprint most recently confirmed in S3."""
        row = self._connection.execute(
            "SELECT content_hash FROM published_playlists WHERE stream_id = ?", (stream_id,)
        ).fetchone()
        return None if row is None else str(row["content_hash"])

    def mark_playlist_published(
        self, *, stream_id: str, content_hash: str, published_at: float
    ) -> None:
        """Record a successful playlist upload so unchanged content is not uploaded again."""
        self._connection.execute(
            """
            INSERT INTO published_playlists(stream_id, content_hash, published_at)
            VALUES (?, ?, ?)
            ON CONFLICT(stream_id) DO UPDATE SET
                content_hash = excluded.content_hash,
                published_at = excluded.published_at
            """,
            (stream_id, content_hash, published_at),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()
