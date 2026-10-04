"""Central logging configuration with per-component environment overrides."""

import logging
import os


def configure_logging() -> None:
    """Configure root logging and ``LOG_LEVEL_UPLOADER_S3=DEBUG`` overrides."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    for name, value in os.environ.items():
        if name.startswith("LOG_LEVEL_"):
            logger_name = name.removeprefix("LOG_LEVEL_").lower().replace("_", ".")
            logging.getLogger(logger_name).setLevel(value.upper())
