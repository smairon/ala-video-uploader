"""FFmpeg adapter that emits recorder-compatible HLS artifacts."""

import logging

# FFmpeg is invoked below with an argument list and without a shell.
import subprocess  # nosec B404
from pathlib import Path

from uploader.specs.constants import (
    FFMPEG_COPY_CODEC,
    FFMPEG_EXECUTABLE,
    FFMPEG_HLS_APPEND_LIST_FLAG,
    FFMPEG_HLS_FORMAT,
    FFMPEG_HLS_SEGMENT_FILENAME_PATTERN,
    FFMPEG_HLS_START_NUMBER_SOURCE,
    FFMPEG_SEGMENT_DURATION_SECONDS,
    LOGGER_EMULATOR,
    PLAYLIST_FILENAME,
)

logger = logging.getLogger(LOGGER_EMULATOR)


class FfmpegRecorderEmulator:
    """Starts FFmpeg with the one-directory-per-stream recorder layout."""

    def run(
        self,
        *,
        sample_path: Path,
        recordings_dir: Path,
        stream_id: str,
        realtime: bool,
        duration_seconds: float | None,
    ) -> int:
        output_dir = recordings_dir / stream_id
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [FFMPEG_EXECUTABLE, "-hide_banner", "-y"]
        if realtime:
            command.append("-re")
        command.extend(["-stream_loop", "-1", "-i", str(sample_path)])
        if duration_seconds is not None:
            command.extend(["-t", str(duration_seconds)])
        command.extend(
            [
                "-c",
                FFMPEG_COPY_CODEC,
                "-f",
                FFMPEG_HLS_FORMAT,
                "-hls_time",
                str(FFMPEG_SEGMENT_DURATION_SECONDS),
                "-hls_list_size",
                "0",
                "-hls_flags",
                FFMPEG_HLS_APPEND_LIST_FLAG,
                "-hls_start_number_source",
                FFMPEG_HLS_START_NUMBER_SOURCE,
                "-hls_segment_filename",
                str(output_dir / FFMPEG_HLS_SEGMENT_FILENAME_PATTERN),
                str(output_dir / PLAYLIST_FILENAME),
            ]
        )
        logger.info(
            "starting ffmpeg recorder emulator", extra={"stream_id": stream_id, "command": command}
        )
        return subprocess.run(command, check=False).returncode  # nosec B603
