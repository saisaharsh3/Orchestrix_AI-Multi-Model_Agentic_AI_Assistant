"""
core/logger.py - Centralized logging.

Handlers are attached once to the root logger; every module logger
propagates to it. Console level follows LOG_LEVEL, the daily file log keeps
DEBUG, and errors also go to a separate file.

Usage:
    from core.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import os
import threading
from datetime import datetime
from pathlib import Path

_configured = False
_lock = threading.Lock()

_CONSOLE_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
_FILE_FORMAT = "%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure() -> None:
    global _configured
    with _lock:
        if _configured:
            return
        # Read the environment directly: config.settings imports this module.
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_dir = Path(os.getenv("LOG_DIR", "logs"))
        stamp = datetime.now().strftime("%Y%m%d")

        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        console = logging.StreamHandler()
        console.setLevel(getattr(logging, level, logging.INFO))
        console.setFormatter(logging.Formatter(_CONSOLE_FORMAT, _DATE_FORMAT))
        root.addHandler(console)

        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_fmt = logging.Formatter(_FILE_FORMAT, _DATE_FORMAT)

            main_file = logging.FileHandler(log_dir / f"orchestrix_{stamp}.log", encoding="utf-8")
            main_file.setLevel(logging.DEBUG)
            main_file.setFormatter(file_fmt)
            root.addHandler(main_file)

            error_file = logging.FileHandler(log_dir / f"errors_{stamp}.log", encoding="utf-8")
            error_file.setLevel(logging.ERROR)
            error_file.setFormatter(file_fmt)
            root.addHandler(error_file)
        except OSError as e:
            root.warning(f"File logging disabled: {e}")

        # Third-party libraries are noisy at DEBUG.
        for noisy in ("httpx", "httpcore", "urllib3", "googleapiclient", "apscheduler", "telegram"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

        _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name)
