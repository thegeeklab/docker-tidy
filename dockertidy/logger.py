#!/usr/bin/env python3
"""Global utility methods and classes."""

import copy
import logging
import os
import sys
from typing import Any, NoReturn

import colorama
from pythonjsonlogger.json import JsonFormatter

from dockertidy.utils import Singleton

JSON_FORMAT = "%(asctime)s %(levelname)s %(message)s"

_LEVEL_COLORS: dict[int, tuple[str, str]] = {
    logging.DEBUG: (colorama.Fore.BLUE, colorama.Style.BRIGHT),
    logging.INFO: (colorama.Fore.CYAN, colorama.Style.BRIGHT),
    logging.WARNING: (colorama.Fore.YELLOW, colorama.Style.BRIGHT),
    logging.ERROR: (colorama.Fore.RED, colorama.Style.BRIGHT),
    logging.CRITICAL: (colorama.Fore.RED, colorama.Style.BRIGHT),
}

_STDOUT_LEVELS = {logging.INFO, logging.WARNING}
_STDERR_LEVELS = {logging.DEBUG, logging.ERROR, logging.CRITICAL}


def _should_do_markup() -> bool:
    py_colors = os.environ.get("PY_COLORS")
    if py_colors is not None:
        return py_colors.strip().lower() in {"1", "true", "yes", "on", "y", "t"}

    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


colorama.init(autoreset=True, strip=not _should_do_markup())


class LevelFilter(logging.Filter):
    """Keep only records whose level belongs to the configured level set."""

    def __init__(self, levels: set[int]) -> None:
        super().__init__()
        self._levels = levels

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno in self._levels


class ConsoleFormatter(logging.Formatter):
    """Colorize the level prefix and reset the color after line breaks."""

    def format(self, record: logging.LogRecord) -> str:
        color, style = _LEVEL_COLORS.get(record.levelno, (colorama.Fore.WHITE, ""))
        reset = colorama.Style.RESET_ALL
        message = record.getMessage().replace("\n", f"\n{reset}... ")
        output = f"{color}{style}[{record.levelname}]{reset} {message}"

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if output[-1:] != "\n":
                output += "\n"
            output += record.exc_text

        return output


class MultilineJsonFormatter(JsonFormatter):
    """JSON formatter that replaces line breaks in messages with spaces."""

    def format(self, record: logging.LogRecord) -> str:
        record = copy.copy(record)
        record.msg = record.msg.replace("\n", " ")
        return JsonFormatter.format(self, record)


class Log:
    """Base logging object."""

    def __init__(
        self, level: int = logging.WARNING, name: str = "dockertidy", json: bool = False
    ) -> None:
        self.logger = logging.getLogger(name)
        self.logger.propagate = False
        self.logger.setLevel(level)
        self._configure(json)

    def _configure(self, json: bool = False) -> None:
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        self.logger.addHandler(self._get_handler(sys.stdout, _STDOUT_LEVELS, json))
        self.logger.addHandler(self._get_handler(sys.stderr, _STDERR_LEVELS, json))

    def _get_handler(self, stream: Any, levels: set[int], json: bool = False) -> logging.Handler:
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        handler.addFilter(LevelFilter(levels))
        handler.setFormatter(self._get_formatter(json))
        return handler

    def _get_formatter(self, json: bool = False) -> logging.Formatter:
        if json:
            return MultilineJsonFormatter(JSON_FORMAT)
        return ConsoleFormatter()

    def set_level(self, s: str | int) -> None:
        """Set log level."""
        self.logger.setLevel(s)

    def sysexit(self, code: int = 1) -> NoReturn:
        """Exit running program with given exit code."""
        sys.exit(code)

    def sysexit_with_message(self, msg: Any, code: int = 1) -> NoReturn:
        """Exit running program with given exit code and message."""
        self.logger.critical(str(msg))
        self.sysexit(code)


class SingleLog(Log, metaclass=Singleton):
    """Singleton logger object."""

    pass
