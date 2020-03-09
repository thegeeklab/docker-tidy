#!/usr/bin/env python3
"""Custom input type parser."""

import datetime

import environs
from dateutil import tz
from pytimeparse import timeparse

env = environs.Env()


def timedelta_validator(value):
    """Return the :class:`datetime.datetime.DateTime` for a time in the past.

    :param value: a string containing a time format supported by
    mod:`pytimeparse`
    """
    if value is None:
        return None

    try:
        _datetime_seconds_ago(timeparse.timeparse(value))
        return value
    except TypeError:
        raise


def timedelta(value, dt_format=None):
    """Return the :class:`datetime.datetime.DateTime` for a time in the past.

    :param value: a string containing a time format supported by
    mod:`pytimeparse`
    """
    if value is None:
        return None

    timedelta = _datetime_seconds_ago(timeparse.timeparse(value))
    if dt_format:
        timedelta = timedelta.strftime(dt_format)

    return timedelta


def _datetime_seconds_ago(seconds):
    now = datetime.datetime.now(tz.tzutc())
    return now - datetime.timedelta(seconds=seconds)


@env.parser_for("timedelta_validator")
def timedelta_parser(value):
    try:
        timedelta_validator(value)
        return value
    except TypeError as e:
        raise environs.EnvError(e)
