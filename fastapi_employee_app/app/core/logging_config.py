"""
app/core/logging_config.py

Centralized logging setup for the whole application.

WHY A SEPARATE MODULE FOR THIS?
------------------------------------
Previously, logging was configured inline inside `middleware/logging.py`
with a bare `logging.basicConfig(level=logging.INFO)` call -- that only
prints to the console and gets silently re-configured (or ignored) if
anything else in the app also calls `basicConfig`. Centralizing setup here,
called once from `main.py` before the app is built, guarantees:

  1. Logs go to BOTH the console (so you see them live in your terminal)
     AND a rotating log file on disk (so you have a persistent record you
     can inspect after the process has stopped, or ship to a log
     aggregator later).
  2. Every logger in the app (`employee_app`, `sqlalchemy.engine`, uvicorn's
     own loggers, etc.) uses the same consistent message format.
  3. Log files don't grow forever -- `RotatingFileHandler` caps each file at
     5 MB and keeps the last 3 backups, then discards older ones.
"""

import logging
import logging.handlers
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(debug: bool = False) -> None:
    """
    Configure the root logger with a console handler and a rotating file
    handler. Call this ONCE, at application startup, before anything else
    logs a message.

    Args:
        debug: when True, the app's own logger ("employee_app") and
            SQLAlchemy's engine logger emit more detail (e.g. SQL statement
            echoing). The ROOT level is always kept at INFO regardless --
            NOT tied to `debug` -- because low-level libraries (aiosqlite,
            passlib, python-multipart, ...) log extremely verbose DEBUG
            messages that aren't useful application logs and would drown
            out everything else. This gives you SQL-query visibility during
            development without a wall of driver-internals noise.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- Console handler: what you see live in your terminal ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # --- Rotating file handler: persists to logs/app.log on disk ---
    # maxBytes=5MB per file, keep up to 3 old copies (app.log.1, .2, .3)
    # before deleting the oldest -- prevents unbounded disk usage.
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Clear any handlers a prior basicConfig() call may have added, so we
    # don't end up with duplicate log lines.
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # This app's own logger: DEBUG-level detail available when DEBUG=True,
    # otherwise plain INFO (request start/end lines, warnings, errors).
    logging.getLogger("employee_app").setLevel(logging.DEBUG if debug else logging.INFO)

    # SQLAlchemy's query echo: only show generated SQL when debugging.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if debug else logging.WARNING
    )

    # Quiet third-party driver/library internals unconditionally -- these
    # are almost never useful even during app-level debugging.
    for noisy_logger in ("aiosqlite", "passlib", "multipart.multipart", "python_multipart"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
