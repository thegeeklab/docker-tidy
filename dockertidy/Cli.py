#!/usr/bin/env python3
"""Entrypoint and CLI handler."""

import argparse
import logging
import os
import sys

import dockertidy.Exception
from dockertidy.Config import SingleConfig
from dockertidy.Utils import SingleLog
from dockertidy.Utils import timedelta_type
from importlib_metadata import version, PackageNotFoundError


class DockerTidy:

    def __init__(self):
        self.log = SingleLog()
        self.logger = self.log.logger
        self.args = self._cli_args()
        self.config = self._get_config()

    def _cli_args(self):
        """
        Use argparse for parsing CLI arguments.

        :return: args objec
        """
        parser = argparse.ArgumentParser(
            description="Generate documentation from annotated Ansible roles using templates")
        parser.add_argument("-v", dest="logging.level", action="append_const", const=-1,
                            help="increase log level")
        parser.add_argument("-q", dest="logging.level", action="append_const",
                            const=1, help="decrease log level")
        parser.add_argument("--version", action="version",
                            version=version(__name__))

        subparsers = parser.add_subparsers(help="sub-command help")

        parser_gc = subparsers.add_parser(
            "gc", help="Run docker garbage collector.")
        parser_gc.add_argument(
            "--max-container-age",
            type=timedelta_type,
            help="Maximum age for a container. Containers older than this age "
            "will be removed. Age can be specified in any pytimeparse "
            "supported format.")
        parser_gc.add_argument(
            "--max-image-age",
            type=timedelta_type,
            help="Maxium age for an image. Images older than this age will be "
            "removed. Age can be specified in any pytimeparse supported "
            "format.")
        parser_gc.add_argument(
            "--dangling-volumes",
            action="store_true",
            help="Dangling volumes will be removed.")
        parser_gc.add_argument(
            "--dry-run", action="store_true",
            help="Only log actions, don't remove anything.")
        parser_gc.add_argument(
            "-t", "--timeout", type=int, default=60,
            help="HTTP timeout in seconds for making docker API calls.")
        parser_gc.add_argument(
            "--exclude-image",
            action="append",
            help="Never remove images with this tag.")
        parser_gc.add_argument(
            "--exclude-image-file",
            type=argparse.FileType("r"),
            help="Path to a file which contains a list of images to exclude, one "
            "image tag per line.")
        parser_gc.add_argument(
            "--exclude-container-label",
            action="append", type=str, default=[],
            help="Never remove containers with this label key or label key=value")

        return parser.parse_args().__dict__

    def _get_config(self):
        try:
            config = SingleConfig(args=self.args)
        except dockertidy.Exception.ConfigError as e:
            self.log.sysexit_with_message(e)

        try:
            self.log.set_level(config.config["logging"]["level"])
        except ValueError as e:
            self.log.sysexit_with_message(
                "Can not set log level.\n{}".format(str(e)))

        self.logger.info("Using config file {}".format(config.config_file))

        return config
