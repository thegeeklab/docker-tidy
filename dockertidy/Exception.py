#!/usr/bin/env python3
"""Custom exceptions."""


class TidyError(Exception):
    """Generic exception class for docker-tidy."""

    def __init__(self, msg, original_exception=""):
        super(TidyError, self).__init__("{msg}\n{org}".format(msg=msg, org=original_exception))
        self.original_exception = original_exception


class ConfigError(TidyError):
    """Errors related to config file handling."""

    pass
