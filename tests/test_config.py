import os
from pathlib import Path

from uploader.specs.settings import Settings


def test_default_state_database_is_not_inside_recordings_directory() -> None:
    original_recordings_dir = os.environ.get("RECORDINGS_DIR")
    original_state_db_path = os.environ.pop("STATE_DB_PATH", None)
    os.environ["RECORDINGS_DIR"] = "/shared/recordings"
    try:
        settings = Settings.from_environment()
    finally:
        if original_recordings_dir is None:
            os.environ.pop("RECORDINGS_DIR", None)
        else:
            os.environ["RECORDINGS_DIR"] = original_recordings_dir
        if original_state_db_path is not None:
            os.environ["STATE_DB_PATH"] = original_state_db_path

    assert settings.recordings_dir == Path("/shared/recordings")
    assert settings.state_db_path == Path("/state/uploader.sqlite3")
