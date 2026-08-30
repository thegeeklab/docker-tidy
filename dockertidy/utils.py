#!/usr/bin/env python3
"""Global utility methods and classes."""

import threading
from typing import Any


def dict_intersect(d1: dict[str, Any], d2: dict[str, Any]) -> dict[str, Any]:
    return {
        k: dict_intersect(d1[k], d2[k]) if isinstance(d1[k], dict) else d1[k]
        for k in d1.keys() & d2.keys()
    }


class Singleton(type):
    """Thread-safe singleton metaclass."""

    _instances: dict[Any, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
