#!/usr/bin/env python3
"""Entrypoint and CLI handler."""

import argparse

import dockertidy.exception
from dockertidy import __version__
from dockertidy.autostop import AutoStop
from dockertidy.config import SingleConfig
from dockertidy.garbage_collector import GarbageCollector
from dockertidy.logger import SingleLog
from dockertidy.parser import timedelta_validator


class DockerTidy:
    """Cli entrypoint to handle command arguments."""

    def __init__(self):
        self.log = SingleLog()
        self.logger = self.log.logger
        self.args = self._cli_args()
        self.config = self._get_config()
        self.gc = GarbageCollector()
        self.stop = AutoStop()
        self.run()

    def _cli_args(self):
        """
        Use argparse for parsing CLI arguments.

        :return: args objec
        """
        parser = argparse.ArgumentParser(description="keep docker hosts tidy")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=None,
            dest="dry_run",
            help="only log actions, don't stop anything"
        )
        parser.add_argument(
            "-t",
            "--timeout",
            type=int,
            dest="http_timeout",
            metavar="HTTP_TIMEOUT",
            help="HTTP timeout in seconds for making docker API calls"
        )
        parser.add_argument(
            "-v", dest="logging.level", action="append_const", const=-1, help="increase log level"
        )
        parser.add_argument(
            "-q", dest="logging.level", action="append_const", const=1, help="decrease log level"
        )
        parser.add_argument(
            "--version", action="version", version="%(prog)s {}".format(__version__)
        )

        subparsers = parser.add_subparsers(dest="command", help="sub-command help")
        subparsers.required = True

        parser_gc = subparsers.add_parser("gc", help="run docker garbage collector")
        parser_gc.add_argument(
            "--max-container-age",
            type=timedelta_validator,
            dest="gc.max_container_age",
            metavar="MAX_CONTAINER_AGE",
            help="maximum age for a container, containers older than this age "
            "will be removed (dateparser value)"
        )
        parser_gc.add_argument(
            "--max-image-age",
            type=timedelta_validator,
            dest="gc.max_image_age",
            metavar="MAX_IMAGE_AGE",
            help="maxium age for an image, images older than this age will be "
            "removed (dateparser value)"
        )
        parser_gc.add_argument(
            "--dangling-volumes",
            action="store_true",
            dest="gc.dangling_volumes",
            help="dangling volumes will be removed"
        )
        parser_gc.add_argument(
            "--exclude-image",
            action="append",
            type=str,
            dest="gc.exclude_images",
            metavar="EXCLUDE_IMAGE",
            help="never remove images with this tag"
        )
        parser_gc.add_argument(
            "--exclude-container-label",
            action="append",
            type=str,
            dest="gc.exclude_container_labels",
            metavar="EXCLUDE_CONTAINER_LABEL",
            help="never remove containers with this label key "
            "or label key=value"
        )

        parser_stop = subparsers.add_parser(
            "stop", help="stop containers that have been running for too long"
        )
        parser_stop.add_argument(
            "--max-run-time",
            type=timedelta_validator,
            dest="stop.max_run_time",
            metavar="MAX_RUN_TIME",
            help="maximum time a container is allows to run (dateparser value)"
        )
        parser_stop.add_argument(
            "--prefix",
            action="append",
            type=str,
            dest="stop.prefix",
            metavar="PREFIX",
            help="only stop containers which match one of the prefix"
        )

        return parser.parse_args().__dict__

    def _get_config(self):
        try:
            config = SingleConfig(args=self.args)
        except dockertidy.exception.ConfigError as e:
            self.log.sysexit_with_message(e)

        try:
            self.log.set_level(config.config["logging"]["level"])
        except ValueError as e:
            self.log.sysexit_with_message("Can not set log level.\n{}".format(str(e)))

        self.logger.info("Using config file {}".format(config.config_file))
        self.logger.debug("Config dump: {}".format(config.config))

        return config

    def run(self):
        """Cli main method."""
        if self.config.config["command"] == "gc":
            self.gc.run()
        elif self.config.config["command"] == "stop":
            self.stop.run()


def main():
    DockerTidy()
