#!/usr/bin/env python3
"""Global utility methods and classes."""

import logging
import os
import sys
from typing import Any, NoReturn

import colorama
from pythonjsonlogger.json import JsonFormatter

from dockertidy.utils import Singleton, to_bool

CONSOLE_FORMAT = "{}[%(levelname)s]{} %(message)s"
JSON_FORMAT = "%(asctime)s %(levelname)s %(message)s"


def _should_do_markup() -> bool:
    py_colors = os.environ.get("PY_COLORS", None)
    if py_colors is not None:
        return to_bool(py_colors)

    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


colorama.init(autoreset=True, strip=not _should_do_markup())


class LogFilter:
    """A custom log filter which excludes log messages above the logged level."""

    def __init__(self, level: int) -> None:
        """
        Initialize a new custom log filter.

        :param level: Log level limit
        :returns: None

        """
        self.__level = level

    def filter(self, logRecord: logging.LogRecord) -> bool:  # noqa
        # https://docs.python.org/3/library/logging.html#logrecord-attributes
        return logRecord.levelno <= self.__level


class MultilineFormatter(logging.Formatter):
    """Logging Formatter to reset color after newline characters."""

    def format(self, record: logging.LogRecord) -> str:
        record.msg = record.msg.replace("\n", f"\n{colorama.Style.RESET_ALL}... ")
        return logging.Formatter.format(self, record)


class MultilineJsonFormatter(JsonFormatter):
    """Logging Formatter to remove newline characters."""

    def format(self, record: logging.LogRecord) -> str:
        record.msg = record.msg.replace("\n", " ")
        return JsonFormatter.format(self, record)


class Log:
    """Base logging object."""

    def __init__(
        self, level: int = logging.WARNING, name: str = "dockertidy", json: bool = False
    ) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.addHandler(self._get_error_handler(json=json))
        self.logger.addHandler(self._get_warning_handler(json=json))
        self.logger.addHandler(self._get_info_handler(json=json))
        self.logger.addHandler(self._get_critical_handler(json=json))
        self.logger.addHandler(self._get_debug_handler(json=json))
        self.logger.propagate = False

    def _get_error_handler(self, json: bool = False) -> logging.Handler:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.ERROR)
        handler.addFilter(LogFilter(logging.ERROR))
        handler.setFormatter(
            MultilineFormatter(
                self.error(CONSOLE_FORMAT.format(colorama.Fore.RED, colorama.Style.RESET_ALL))
            )
        )

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def _get_warning_handler(self, json: bool = False) -> logging.Handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.WARNING)
        handler.addFilter(LogFilter(logging.WARNING))
        handler.setFormatter(
            MultilineFormatter(
                self.warning(CONSOLE_FORMAT.format(colorama.Fore.YELLOW, colorama.Style.RESET_ALL))
            )
        )

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def _get_info_handler(self, json: bool = False) -> logging.Handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.addFilter(LogFilter(logging.INFO))
        handler.setFormatter(
            MultilineFormatter(
                self.info(CONSOLE_FORMAT.format(colorama.Fore.CYAN, colorama.Style.RESET_ALL))
            )
        )

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def _get_critical_handler(self, json: bool = False) -> logging.Handler:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.CRITICAL)
        handler.addFilter(LogFilter(logging.CRITICAL))
        handler.setFormatter(
            MultilineFormatter(
                self.critical(CONSOLE_FORMAT.format(colorama.Fore.RED, colorama.Style.RESET_ALL))
            )
        )

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def _get_debug_handler(self, json: bool = False) -> logging.Handler:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        handler.addFilter(LogFilter(logging.DEBUG))
        handler.setFormatter(
            MultilineFormatter(
                self.critical(CONSOLE_FORMAT.format(colorama.Fore.BLUE, colorama.Style.RESET_ALL))
            )
        )

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def set_level(self, s: str | int) -> None:
        """Set log level."""
        self.logger.setLevel(s)

    def debug(self, msg: str) -> str:
        """Format info messages and return string."""
        return msg

    def critical(self, msg: str) -> str:
        """Format critical messages and return string."""
        return msg

    def error(self, msg: str) -> str:
        """Format error messages and return string."""
        return msg

    def warning(self, msg: str) -> str:
        """Format warning messages and return string."""
        return msg

    def info(self, msg: str) -> str:
        """Format info messages and return string."""
        return msg

    def _color_text(self, color: str, msg: str) -> str:
        """
        Colorize strings.

        :param color: colorama color settings
        :param msg: string to colorize
        :returns: string

        """
        return f"{color}{msg}{colorama.Style.RESET_ALL}"

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
