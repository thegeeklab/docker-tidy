#!/usr/bin/env python3
"""Custom input type parser."""

from argparse import ArgumentTypeError

import dateparser
import environs

env = environs.Env()


def timedelta_validator(value):
    """Return the dateparser string for a time in the past.

    :param value: a string containing a time format supported by
    mod:`dateparser`
    """
    if value is None:
        return None

    if not dateparser.parse(value):
        raise ArgumentTypeError("'{}' is not a valid timedelta string".format(value))

    return value


def timedelta(value, dt_format=None):
    """Return the :class:`datetime.datetime.DateTime` for a time in the past.

    :param value: a string containing a time format supported by
    mod:`dateparser`
    """
    if value is None:
        return None

    timedelta = dateparser.parse(
        value, settings={
            "TO_TIMEZONE": "UTC",
            "RETURN_AS_TIMEZONE_AWARE": True
        }
    )

    if dt_format:
        timedelta = timedelta.strftime(dt_format)

    return timedelta


@env.parser_for("timedelta_validator")
def timedelta_parser(value):
    try:
        timedelta_validator(value)
        return value
    except ArgumentTypeError as e:
        raise environs.EnvError(e)
