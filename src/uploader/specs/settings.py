"""Environment-backed deployment settings."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from uploader.specs.constants import (
    DEFAULT_LAST_SEGMENT_STABLE_SECONDS,
    DEFAULT_MAX_RECORDING_SECONDS,
    DEFAULT_METRICS_PORT,
    DEFAULT_PLAYLIST_RETENTION_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_RECORDINGS_DIRECTORY,
    DEFAULT_S3_ACCESS_KEY_ID,
    DEFAULT_S3_BUCKET,
    DEFAULT_S3_ENDPOINT_URL,
    DEFAULT_S3_SECRET_ACCESS_KEY,
    DEFAULT_STATE_DATABASE_PATH,
    DEFAULT_UPLOAD_CONCURRENCY,
    ENV_LAST_SEGMENT_STABLE_SECONDS,
    ENV_MAX_RECORDING_SECONDS,
    ENV_METRICS_PORT,
    ENV_PLAYLIST_RETENTION_SECONDS,
    ENV_POLL_INTERVAL_SECONDS,
    ENV_RECORDINGS_DIRECTORY,
    ENV_S3_ACCESS_KEY_ID,
    ENV_S3_BUCKET,
    ENV_S3_ENDPOINT_URL,
    ENV_S3_SECRET_ACCESS_KEY,
    ENV_STATE_DATABASE_PATH,
    ENV_UPLOAD_CONCURRENCY,
)


@dataclass(frozen=True, slots=True)
class Settings:
    recordings_dir: Path
    state_db_path: Path
    s3_endpoint_url: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    poll_interval_seconds: float
    last_segment_stable_seconds: float
    max_recording_seconds: int
    playlist_retention_seconds: int
    metrics_port: int
    upload_concurrency: int

    @classmethod
    def from_environment(cls) -> Self:
        recordings_dir = Path(
            os.environ.get(ENV_RECORDINGS_DIRECTORY, DEFAULT_RECORDINGS_DIRECTORY)
        )
        return cls(
            recordings_dir=recordings_dir,
            state_db_path=Path(
                os.environ.get(ENV_STATE_DATABASE_PATH, DEFAULT_STATE_DATABASE_PATH)
            ),
            s3_endpoint_url=os.environ.get(ENV_S3_ENDPOINT_URL, DEFAULT_S3_ENDPOINT_URL),
            s3_bucket=os.environ.get(ENV_S3_BUCKET, DEFAULT_S3_BUCKET),
            s3_access_key_id=os.environ.get(ENV_S3_ACCESS_KEY_ID, DEFAULT_S3_ACCESS_KEY_ID),
            s3_secret_access_key=os.environ.get(
                ENV_S3_SECRET_ACCESS_KEY, DEFAULT_S3_SECRET_ACCESS_KEY
            ),
            poll_interval_seconds=float(
                os.environ.get(ENV_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS)
            ),
            last_segment_stable_seconds=float(
                os.environ.get(
                    ENV_LAST_SEGMENT_STABLE_SECONDS,
                    DEFAULT_LAST_SEGMENT_STABLE_SECONDS,
                )
            ),
            max_recording_seconds=int(
                os.environ.get(ENV_MAX_RECORDING_SECONDS, DEFAULT_MAX_RECORDING_SECONDS)
            ),
            playlist_retention_seconds=int(
                os.environ.get(ENV_PLAYLIST_RETENTION_SECONDS, DEFAULT_PLAYLIST_RETENTION_SECONDS)
            ),
            metrics_port=int(os.environ.get(ENV_METRICS_PORT, DEFAULT_METRICS_PORT)),
            upload_concurrency=int(
                os.environ.get(ENV_UPLOAD_CONCURRENCY, DEFAULT_UPLOAD_CONCURRENCY)
            ),
        )
