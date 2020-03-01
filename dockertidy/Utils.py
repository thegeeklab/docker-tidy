#!/usr/bin/env python3
"""Global utility methods and classes."""

import datetime
import logging
import os
import pprint
import sys
from distutils.util import strtobool

import colorama
from dateutil import tz
from pythonjsonlogger import jsonlogger
from pytimeparse import timeparse

import dockertidy.Exception

CONSOLE_FORMAT = "{}[%(levelname)s]{} %(message)s"
JSON_FORMAT = "(asctime) (levelname) (message)"


def to_bool(string):
    return bool(strtobool(str(string)))


def timedelta_type(value):
    """Return the :class:`datetime.datetime.DateTime` for a time in the past.

    :param value: a string containing a time format supported by
    mod:`pytimeparse`
    """
    if value is None:
        return None
    return _datetime_seconds_ago(timeparse.timeparse(value))


def _datetime_seconds_ago(seconds):
    now = datetime.datetime.now(tz.tzutc())
    return now - datetime.timedelta(seconds=seconds)


def _should_do_markup():
    py_colors = os.environ.get("PY_COLORS", None)
    if py_colors is not None:
        return to_bool(py_colors)

    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


colorama.init(autoreset=True, strip=not _should_do_markup())


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class LogFilter(object):
    """A custom log filter which excludes log messages above the logged level."""

    def __init__(self, level):
        """
        Initialize a new custom log filter.

        :param level: Log level limit
        :returns: None

        """
        self.__level = level

    def filter(self, logRecord):  # noqa
        # https://docs.python.org/3/library/logging.html#logrecord-attributes
        return logRecord.levelno <= self.__level


class MultilineFormatter(logging.Formatter):
    """Logging Formatter to reset color after newline characters."""

    def format(self, record): # noqa
        record.msg = record.msg.replace("\n", "\n{}... ".format(colorama.Style.RESET_ALL))
        return logging.Formatter.format(self, record)


class MultilineJsonFormatter(jsonlogger.JsonFormatter):
    """Logging Formatter to remove newline characters."""

    def format(self, record): # noqa
        record.msg = record.msg.replace("\n", " ")
        return jsonlogger.JsonFormatter.format(self, record)


class Log:
    def __init__(self, level=logging.WARN, name="dockertidy", json=False):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.addHandler(self._get_error_handler(json=json))
        self.logger.addHandler(self._get_warn_handler(json=json))
        self.logger.addHandler(self._get_info_handler(json=json))
        self.logger.addHandler(self._get_critical_handler(json=json))
        self.logger.addHandler(self._get_debug_handler(json=json))
        self.logger.propagate = False

    def _get_error_handler(self, json=False):
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.ERROR)
        handler.addFilter(LogFilter(logging.ERROR))
        handler.setFormatter(MultilineFormatter(
            self.error(CONSOLE_FORMAT.format(colorama.Fore.RED, colorama.Style.RESET_ALL))))

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def _get_warn_handler(self, json=False):
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.WARN)
        handler.addFilter(LogFilter(logging.WARN))
        handler.setFormatter(MultilineFormatter(
            self.warn(CONSOLE_FORMAT.format(colorama.Fore.YELLOW, colorama.Style.RESET_ALL))))

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def _get_info_handler(self, json=False):
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.addFilter(LogFilter(logging.INFO))
        handler.setFormatter(MultilineFormatter(
            self.info(CONSOLE_FORMAT.format(colorama.Fore.CYAN, colorama.Style.RESET_ALL))))

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def _get_critical_handler(self, json=False):
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.CRITICAL)
        handler.addFilter(LogFilter(logging.CRITICAL))
        handler.setFormatter(MultilineFormatter(
            self.critical(CONSOLE_FORMAT.format(colorama.Fore.RED, colorama.Style.RESET_ALL))))

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def _get_debug_handler(self, json=False):
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        handler.addFilter(LogFilter(logging.DEBUG))
        handler.setFormatter(MultilineFormatter(
            self.critical(CONSOLE_FORMAT.format(colorama.Fore.BLUE, colorama.Style.RESET_ALL))))

        if json:
            handler.setFormatter(MultilineJsonFormatter(JSON_FORMAT))

        return handler

    def set_level(self, s):
        self.logger.setLevel(s)

    def debug(self, msg):
        """Format info messages and return string."""
        return msg

    def critical(self, msg):
        """Format critical messages and return string."""
        return msg

    def error(self, msg):
        """Format error messages and return string."""
        return msg

    def warn(self, msg):
        """Format warn messages and return string."""
        return msg

    def info(self, msg):
        """Format info messages and return string."""
        return msg

    def _color_text(self, color, msg):
        """
        Colorize strings.

        :param color: colorama color settings
        :param msg: string to colorize
        :returns: string

        """
        return "{}{}{}".format(color, msg, colorama.Style.RESET_ALL)

    def sysexit(self, code=1):
        sys.exit(code)

    def sysexit_with_message(self, msg, code=1):
        self.logger.critical(str(msg))
        self.sysexit(code)


class SingleLog(Log, metaclass=Singleton):
    pass


class FileUtils:
    @staticmethod
    def create_path(path):
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def query_yes_no(question, default=True):
        """Ask a yes/no question via input() and return their answer.

        "question" is a string that is presented to the user.
        "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

        The "answer" return value is one of "yes" or "no".
        """
        if default:
            prompt = "[Y/n]"
        else:
            prompt = "[N/y]"

        try:
            # input() is safe in python3
            choice = input("{} {} ".format(question, prompt)) or default  # nosec
            return to_bool(choice)
        except (KeyboardInterrupt, ValueError) as e:
            raise dockertidy.Exception.InputError("Error while reading input", e)
