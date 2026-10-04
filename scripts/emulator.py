"""FFmpeg recorder emulator entrypoint, launched with ``python -m scripts.emulator``."""

import argparse
from pathlib import Path

from uploader.emulator.ffmpeg_writer import FfmpegRecorderEmulator
from uploader.infrastructure.logging import configure_logging


def main() -> None:
    """Parse emulator options and return FFmpeg's exit status to the shell."""
    parser = argparse.ArgumentParser(description="Generate an HLS recording with FFmpeg")
    parser.add_argument("--stream-id", required=True)
    parser.add_argument("--sample", type=Path, default=Path("data/sample.mp4"))
    parser.add_argument("--recordings-dir", type=Path, default=Path("data/recordings"))
    parser.add_argument(
        "--fast", action="store_true", help="Generate as fast as FFmpeg can process"
    )
    parser.add_argument("--duration", type=float, help="Stop after this many media seconds")
    args = parser.parse_args()
    configure_logging()

    exit_code = FfmpegRecorderEmulator().run(
        sample_path=args.sample,
        recordings_dir=args.recordings_dir,
        stream_id=args.stream_id,
        realtime=not args.fast,
        duration_seconds=args.duration,
    )
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
