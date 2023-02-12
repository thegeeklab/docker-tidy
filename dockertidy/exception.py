#!/usr/bin/env python3
"""Custom exceptions."""


class TidyError(Exception):
    """Generic exception class for docker-tidy."""

    def __init__(self, msg, original_exception=""):
        super().__init__(f"{msg}\n{original_exception}")
        self.original_exception = original_exception


class ConfigError(TidyError):
    """Errors related to config file handling."""

    pass
