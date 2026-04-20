"""Logging configuration and utilities."""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger
import json


def setup_logger(
    name: str = "phd_hunter",
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logger:
    """Configure logger with console and optional file output.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        format_string: Custom format string

    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()

    # Default format
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Console handler
    logger.add(
        sys.stdout,
        format=format_string,
        level=level.upper(),
        colorize=True,
    )

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
            level=level.upper(),
            rotation="1 day",
            retention="7 days",
            compression="zip",
            serialize=False,
        )

    return logger


def get_logger(name: str) -> logger:
    """Get logger for module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logger.bind(name=name)


class StructuredLogger:
    """Logger that outputs structured JSON for machine parsing."""

    def __init__(self, name: str, log_file: Optional[str] = None):
        self.name = name
        self.log_file = log_file

    def _log(self, level: str, message: str, **kwargs) -> None:
        """Log structured message."""
        log_entry = {
            "timestamp": logger._core.handler[0]._format_time(),
            "level": level,
            "name": self.name,
            "message": message,
            **kwargs
        }

        # Console
        print(json.dumps(log_entry, default=str))

        # File
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, default=str) + '\n')

    def info(self, message: str, **kwargs) -> None:
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._log("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        self._log("DEBUG", message, **kwargs)
