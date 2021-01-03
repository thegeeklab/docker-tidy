#!/usr/bin/env python3
"""Global utility methods and classes."""

from distutils.util import strtobool


def to_bool(string):
    return bool(strtobool(str(string)))


def dict_intersect(d1, d2):
    return {
        k: dict_intersect(d1[k], d2[k]) if isinstance(d1[k], dict) else d1[k]
        for k in d1.keys() & d2.keys()
    }


class Singleton(type):
    """Singleton metaclass."""

    _instances = {}

    def __call__(cls, *args, **kwargs):  # noqa

        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
