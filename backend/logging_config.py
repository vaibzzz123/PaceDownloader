"""Centralized logging configuration for the One Pace Jellyfin backend."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Log file configuration
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "backend.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 3  # Keep 3 backup files (backend.log.1, .2, .3)


def setup_logging(log_level: str = "INFO"):
    """
    Configure application-wide logging with console and rotating file output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Log files:
        - logs/backend.log (current)
        - logs/backend.log.1, .2, .3 (rotated backups)
        - Max 5MB per file, 3 backups = ~20MB total
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logs directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Log format
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    # File always captures DEBUG for troubleshooting, regardless of console level
    file_handler.setLevel(logging.DEBUG)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Allow all levels, handlers filter
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("git").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
