"""Named values shared across deployment, application, and adapters."""

# Converts duration defaults expressed in minutes to seconds.
SECONDS_PER_MINUTE = 60
# Converts duration defaults expressed in hours to minutes.
MINUTES_PER_HOUR = 60
# Defines the maximum valid lifetime of one recorder stream.
DEFAULT_MAX_RECORDING_HOURS = 10
# Keeps a finalized local playlist available after a stream ends.
DEFAULT_PLAYLIST_RETENTION_HOURS = 24
# Supplies the default deadline used to append HLS ENDLIST.
DEFAULT_MAX_RECORDING_SECONDS = DEFAULT_MAX_RECORDING_HOURS * MINUTES_PER_HOUR * SECONDS_PER_MINUTE
# Supplies the default local playlist cleanup deadline.
DEFAULT_PLAYLIST_RETENTION_SECONDS = (
    DEFAULT_PLAYLIST_RETENTION_HOURS * MINUTES_PER_HOUR * SECONDS_PER_MINUTE
)

# Is the container path where the recorder's shared HLS volume is mounted.
DEFAULT_RECORDINGS_DIRECTORY = "/recordings"
# Is the uploader-private default path for durable SQLite state.
DEFAULT_STATE_DATABASE_PATH = "/state/uploader.sqlite3"
# Targets the local SeaweedFS S3 API during local development.
DEFAULT_S3_ENDPOINT_URL = "http://localhost:8333"
# Names the S3 bucket that receives published HLS objects.
DEFAULT_S3_BUCKET = "video"
# Provides local SeaweedFS's default S3 access key.
DEFAULT_S3_ACCESS_KEY_ID = "admin"
# Requires deployments to provide an S3 secret explicitly.
DEFAULT_S3_SECRET_ACCESS_KEY = ""  # nosec B105
# Controls how often the worker scans recorder directories by default.
DEFAULT_POLL_INTERVAL_SECONDS = 2
# Requires the currently last segment to remain unchanged before uploading it.
DEFAULT_LAST_SEGMENT_STABLE_SECONDS = 4
# Exposes Prometheus metrics on this default TCP port.
DEFAULT_METRICS_PORT = 8000
# Caps simultaneous S3 uploads for one uploader process.
DEFAULT_UPLOAD_CONCURRENCY = 8
# Selects the S3 signing region expected by SeaweedFS.
S3_REGION_NAME = "us-east-1"

# Overrides the shared recordings mount path at deployment time.
ENV_RECORDINGS_DIRECTORY = "RECORDINGS_DIR"
# Overrides the uploader-private SQLite database path.
ENV_STATE_DATABASE_PATH = "STATE_DB_PATH"
# Overrides the S3-compatible endpoint URL.
ENV_S3_ENDPOINT_URL = "S3_ENDPOINT_URL"
# Overrides the destination S3 bucket name.
ENV_S3_BUCKET = "S3_BUCKET"
# Overrides the S3 access key used by the uploader.
ENV_S3_ACCESS_KEY_ID = "S3_ACCESS_KEY_ID"
# Overrides the S3 secret key used by the uploader.
ENV_S3_SECRET_ACCESS_KEY = "S3_SECRET_ACCESS_KEY"  # nosec B105
# Overrides the interval between recorder directory scans.
ENV_POLL_INTERVAL_SECONDS = "POLL_INTERVAL_SECONDS"
# Overrides the required stable period for the currently last segment.
ENV_LAST_SEGMENT_STABLE_SECONDS = "LAST_SEGMENT_STABLE_SECONDS"
# Overrides the recording deadline before finalization.
ENV_MAX_RECORDING_SECONDS = "MAX_RECORDING_SECONDS"
# Overrides how long a finalized playlist stays on local disk.
ENV_PLAYLIST_RETENTION_SECONDS = "PLAYLIST_RETENTION_SECONDS"
# Overrides the Prometheus HTTP endpoint port.
ENV_METRICS_PORT = "METRICS_PORT"
# Overrides the maximum number of concurrent object uploads.
ENV_UPLOAD_CONCURRENCY = "UPLOAD_CONCURRENCY"

# Is the recorder-owned media playlist file name.
PLAYLIST_FILENAME = "playlist.m3u8"
# Is the uploader's temporary rendered playlist file name.
PUBLISHED_PLAYLIST_FILENAME = ".playlist.published.m3u8"
# Selects MPEG-TS chunks while calculating local backlog metrics.
SEGMENT_FILE_GLOB = "*.ts"
# Is the deterministic top-level S3 prefix for every stream.
S3_STREAMS_PREFIX = "streams"
# Lets immutable uploaded segments be cached for one year.
S3_SEGMENT_CACHE_CONTROL = "public, max-age=31536000, immutable"
# Ensures HLS clients revalidate the changing playlist on every request.
S3_PLAYLIST_CACHE_CONTROL = "no-cache"
# Declares the HTTP media type of MPEG-TS segment objects.
SEGMENT_CONTENT_TYPE = "video/mp2t"
# Declares the HTTP media type of HLS playlist objects.
PLAYLIST_CONTENT_TYPE = "application/vnd.apple.mpegurl"

# Marks a published HLS playlist as permanently complete.
HLS_ENDLIST_TAG = "#EXT-X-ENDLIST"
# Identifies HLS directives and comments in playlist source.
HLS_COMMENT_PREFIX = "#"
# Preserves the canonical HLS line separator when rendering playlists.
HLS_LINE_SEPARATOR = "\n"
# Defines the encoding shared by playlist reads and temporary writes.
TEXT_ENCODING_UTF8 = "utf-8"

# Labels segment upload and deletion metric series.
METRIC_OBJECT_TYPE_SEGMENT = "segment"
# Labels playlist upload and deletion metric series.
METRIC_OBJECT_TYPE_PLAYLIST = "playlist"
# Labels successful upload metric series.
METRIC_OUTCOME_SUCCESS = "success"
# Labels failed upload metric series.
METRIC_OUTCOME_ERROR = "error"
# Labels stream publication failures in metrics.
METRIC_OPERATION_PUBLISH = "publish"
# Labels finalized-stream cleanup failures in metrics.
METRIC_OPERATION_CLEANUP = "cleanup"
# Labels streams currently eligible for publishing.
METRIC_STREAM_STATE_ACTIVE = "active"
# Labels finalized local stream directories retained for cleanup.
METRIC_STREAM_STATE_FINALIZED = "finalized"

# Prefixes named asyncio tasks that publish one stream.
TASK_NAME_PUBLISH_PREFIX = "publish:"
# Names the logger responsible for polling and task orchestration.
LOGGER_DAEMON = "uploader.daemon"
# Names the logger responsible for segment and playlist publication.
LOGGER_PUBLISHER = "uploader.publisher"
# Names the logger responsible for finalized-stream retention cleanup.
LOGGER_CLEANUP = "uploader.cleanup"
# Names the logger responsible for the FFmpeg recorder emulator.
LOGGER_EMULATOR = "uploader.emulator"
# Names the logger responsible for worker process lifecycle events.
LOGGER_WORKER = "uploader.worker"

# Selects the FFmpeg binary used by the recorder emulator.
FFMPEG_EXECUTABLE = "ffmpeg"
# Sets the intended HLS segment duration generated by the emulator.
FFMPEG_SEGMENT_DURATION_SECONDS = 10
# Keeps generated segment names unique and monotonically increasing.
FFMPEG_HLS_SEGMENT_FILENAME_PATTERN = "segment-%012d.ts"
# Seeds HLS sequence numbers from epoch microseconds for uniqueness.
FFMPEG_HLS_START_NUMBER_SOURCE = "epoch_us"
# Copies compatible source streams instead of re-encoding them.
FFMPEG_COPY_CODEC = "copy"
# Selects FFmpeg's native HLS output muxer.
FFMPEG_HLS_FORMAT = "hls"
# Makes FFmpeg keep all previous entries in the growing playlist.
FFMPEG_HLS_APPEND_LIST_FLAG = "append_list"

# Enables SQLite write-ahead logging for safe concurrent readers.
SQLITE_JOURNAL_MODE_WAL = "WAL"
# Requires SQLite to flush committed state before acknowledging writes.
SQLITE_SYNCHRONOUS_MODE_FULL = "FULL"
# Selects the aiobotocore service model for S3-compatible APIs.
S3_SERVICE_NAME = "s3"
# Is the response property containing an uploaded object's ETag.
S3_ETAG_RESPONSE_KEY = "ETag"
# Treats an already-created bucket as a successful idempotent initialization.
S3_ALREADY_EXISTS_ERROR_CODES = frozenset({"BucketAlreadyExists", "BucketAlreadyOwnedByYou"})

# Is the Prometheus counter name for completed upload attempts.
METRIC_NAME_UPLOADS_TOTAL = "uploader_uploads_total"
# Is the Prometheus histogram name for individual upload latency.
METRIC_NAME_UPLOAD_DURATION_SECONDS = "uploader_upload_duration_seconds"
# Is the Prometheus counter name for bytes sent to object storage.
METRIC_NAME_UPLOADED_BYTES_TOTAL = "uploader_uploaded_bytes_total"
# Is the Prometheus gauge name for segments awaiting S3 confirmation.
METRIC_NAME_PENDING_SEGMENTS = "uploader_pending_segments"
# Is the Prometheus gauge name for backlog age monitoring.
METRIC_NAME_OLDEST_PENDING_SEGMENT_SECONDS = "uploader_oldest_pending_segment_seconds"
# Is the Prometheus counter name for successful local artifact cleanup.
METRIC_NAME_LOCAL_FILES_DELETED_TOTAL = "uploader_local_files_deleted_total"
# Is the Prometheus counter name for isolated per-stream failures.
METRIC_NAME_STREAM_PROCESSING_ERRORS_TOTAL = "uploader_stream_processing_errors_total"
# Is the Prometheus gauge name for locally discovered stream lifecycle states.
METRIC_NAME_STREAMS = "uploader_streams"
# Names the label that distinguishes segments from playlists.
METRIC_LABEL_OBJECT_TYPE = "object_type"
# Names the label that distinguishes success from error outcomes.
METRIC_LABEL_OUTCOME = "outcome"
# Names the label that distinguishes publish from cleanup operations.
METRIC_LABEL_OPERATION = "operation"
# Names the label that distinguishes active from finalized streams.
METRIC_LABEL_STATE = "state"
