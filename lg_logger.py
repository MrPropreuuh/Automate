import os
import logging
from logging.handlers import RotatingFileHandler
import sys

# Constants for log management
LOG_FILE = "lostgard_voter.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3  # Keep 3 old log files

class CustomFormatter(logging.Formatter):
    """Custom logging formatter with colors for terminal and clean timestamps."""
    
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: blue + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

def setup_logger(name="LGVoter"):
    """
    Sets up a logger with both console and rotating file handlers.
    Ensures storage is cleaned automatically.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Check if handlers already exist to avoid duplication
    if not logger.handlers:
        # 1. Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(CustomFormatter())
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        # 2. Rotating File Handler (The "Auto-Clean" mechanism)
        file_handler = RotatingFileHandler(
            LOG_FILE, 
            maxBytes=MAX_LOG_SIZE, 
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    return logger

# Singleton instance for the whole project
logger = setup_logger()

def trace(msg):
    """Specifically for step-by-step 'Ultra Debugging'."""
    logger.debug(f"[TRACE] {msg}")

def status(msg):
    """For high-level stage monitoring."""
    logger.info(f"==> {msg}")
