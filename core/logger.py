"""
core/logger.py - Centralized Logging System
Provides consistent logging across all modules with file persistence
"""

import logging
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log files
MAIN_LOG = LOG_DIR / f"orchestrix_{datetime.now().strftime('%Y%m%d')}.log"
ERROR_LOG = LOG_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.log"


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Usage:
        from core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Operation started")
        logger.error("Operation failed", exc_info=True)
    """
    logger = logging.getLogger(name)
    
    # Only configure once
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Console handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        
        # File handler (DEBUG and above)
        file_handler = logging.FileHandler(MAIN_LOG, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        
        # Error file handler (ERROR and above only)
        error_handler = logging.FileHandler(ERROR_LOG, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
    
    return logger


# Convenience logger for quick imports
logger = get_logger("orchestrix")
