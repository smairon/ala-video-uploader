"""Prometheus adapter for uploader operational metrics."""

from typing import cast

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from uploader.specs.constants import (
    METRIC_LABEL_OBJECT_TYPE,
    METRIC_LABEL_OPERATION,
    METRIC_LABEL_OUTCOME,
    METRIC_LABEL_STATE,
    METRIC_NAME_LOCAL_FILES_DELETED_TOTAL,
    METRIC_NAME_OLDEST_PENDING_SEGMENT_SECONDS,
    METRIC_NAME_PENDING_SEGMENTS,
    METRIC_NAME_STREAM_PROCESSING_ERRORS_TOTAL,
    METRIC_NAME_STREAMS,
    METRIC_NAME_UPLOAD_DURATION_SECONDS,
    METRIC_NAME_UPLOADED_BYTES_TOTAL,
    METRIC_NAME_UPLOADS_TOTAL,
)
from uploader.specs.contracts import LabelledMetricContract


class UploaderMetrics:
    """Owns bounded-cardinality process metrics exposed to Prometheus."""

    def __init__(self) -> None:
        self.uploads = cast(
            LabelledMetricContract,
            Counter(
                METRIC_NAME_UPLOADS_TOTAL,
                "Completed upload attempts",
                (METRIC_LABEL_OBJECT_TYPE, METRIC_LABEL_OUTCOME),
            ),
        )
        self.upload_duration = cast(
            LabelledMetricContract,
            Histogram(
                METRIC_NAME_UPLOAD_DURATION_SECONDS,
                "Time spent uploading an object",
                (METRIC_LABEL_OBJECT_TYPE,),
            ),
        )
        self.uploaded_bytes = cast(
            LabelledMetricContract,
            Counter(METRIC_NAME_UPLOADED_BYTES_TOTAL, "Bytes uploaded to S3"),
        )
        self.pending_segments = cast(
            LabelledMetricContract,
            Gauge(METRIC_NAME_PENDING_SEGMENTS, "Segments not yet confirmed in S3"),
        )
        self.oldest_pending_seconds = cast(
            LabelledMetricContract,
            Gauge(METRIC_NAME_OLDEST_PENDING_SEGMENT_SECONDS, "Age of the oldest pending segment"),
        )
        self.deleted_files = cast(
            LabelledMetricContract,
            Counter(
                METRIC_NAME_LOCAL_FILES_DELETED_TOTAL,
                "Locally deleted files",
                (METRIC_LABEL_OBJECT_TYPE,),
            ),
        )
        self.stream_processing_errors = cast(
            LabelledMetricContract,
            Counter(
                METRIC_NAME_STREAM_PROCESSING_ERRORS_TOTAL,
                "Stream operations that failed without stopping the daemon",
                (METRIC_LABEL_OPERATION,),
            ),
        )
        self.streams = cast(
            LabelledMetricContract,
            Gauge(METRIC_NAME_STREAMS, "Streams tracked by the uploader", (METRIC_LABEL_STATE,)),
        )

    def start_server(self, port: int) -> None:
        start_http_server(port)
