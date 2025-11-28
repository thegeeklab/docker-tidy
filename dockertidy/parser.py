#!/usr/bin/env python3
"""Custom input type parser."""

from argparse import ArgumentTypeError

import dateparser
import environs

env = environs.Env()


def timedelta_validator(value: str | None) -> str | None:
    """
    Return the dateparser string for a time in the past.

    :param value: a string containing a time format supported by
    mod:`dateparser`
    """
    if value is None:
        return None

    if not dateparser.parse(value):
        raise ArgumentTypeError(f"'{value}' is not a valid timedelta string")

    return value


@env.parser_for("timedelta_validator")
def timedelta_parser(value: str) -> str:
    try:
        timedelta_validator(value)
        return value
    except ArgumentTypeError as e:
        raise environs.EnvError(e) from e
