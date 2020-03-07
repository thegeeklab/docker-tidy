#!/usr/bin/env python3
"""Default package."""

try:
    from importlib import metadata
except ImportError:  # for Python<3.8
    import importlib_metadata as metadata

__author__ = "Robert Kaussow"
__project__ = "docker-tidy"
__license__ = "Apache-2.0"
__maintainer__ = "Robert Kaussow"
__email__ = "mail@geeklabor.de"
__url__ = "https://github.com/xoxys/docker-tidy"
__version__ = metadata.version("docker-tidy")
