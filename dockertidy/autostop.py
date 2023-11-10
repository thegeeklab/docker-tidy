#!/usr/bin/env python3
"""Stop long running docker iamges."""

import dateutil.parser
import docker
import docker.errors
import requests.exceptions

from dockertidy.config import SingleConfig
from dockertidy.logger import SingleLog
from dockertidy.parser import timedelta


class AutoStop:
    """Autostop object to handle long running containers."""

    def __init__(self):
        self.config = SingleConfig()
        self.log = SingleLog()
        self.logger = SingleLog().logger
        self.docker = self._get_docker_client()

    def stop_containers(self):
        """Identify long running containers and terminate them."""
        client = self.docker
        config = self.config.config

        max_run_time = timedelta(config["stop"]["max_run_time"])
        prefix = config["stop"]["prefix"]
        dry_run = config["dry_run"]

        matcher = self._build_container_matcher(prefix)

        self.logger.info(
            "Stopping containers older than '{}'".format(
                timedelta(config["stop"]["max_run_time"], dt_format="%Y-%m-%d, %H:%M:%S")
            )
        )
        for container_summary in client.containers():
            container = client.inspect_container(container_summary["Id"])
            name = container["Name"].lstrip("/")

            if (
                prefix and matcher(name) and self._has_been_running_since(container, max_run_time)
            ) or (not prefix and self._has_been_running_since(container, max_run_time)):
                self.logger.info(
                    "Stopping container {id} {name}: running since {started}".format(
                        id=container["Id"][:16], name=name, started=container["State"]["StartedAt"]
                    )
                )

                if not dry_run:
                    self._stop_container(client, container["Id"])

    def _stop_container(self, client, cid):
        try:
            client.stop(cid)
        except requests.exceptions.Timeout as e:
            self.logger.warning(f"Failed to stop container {cid}: {e!s}")
        except docker.errors.APIError as e:
            self.logger.warning(f"Error stopping {cid}: {e!s}")

    def _build_container_matcher(self, prefixes):
        def matcher(name):
            return any(name.startswith(prefix) for prefix in prefixes)

        return matcher

    def _has_been_running_since(self, container, min_time):
        started_at = container.get("State", {}).get("StartedAt")
        if not started_at:
            return False

        return dateutil.parser.parse(started_at) <= min_time

    def _get_docker_client(self):
        config = self.config.config
        return docker.APIClient(version="auto", timeout=config["http_timeout"])

    def run(self):
        """Autostop main method."""
        self.logger.info("Start autostop")
        config = self.config.config

        if config["stop"]["max_run_time"]:
            self.stop_containers()

        if not config["stop"]["max_run_time"]:
            self.logger.warning("Skipped, no arguments given")
