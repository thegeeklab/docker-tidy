#!/usr/bin/env python3
"""Global utility methods and classes."""

from distutils.util import strtobool


def to_bool(string):
    return bool(strtobool(str(string)))


class Singleton(type):
    """Singleton metaclass."""

    _instances = {}

    def __call__(cls, *args, **kwargs):  # noqa

        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
