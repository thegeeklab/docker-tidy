#!/usr/bin/env python3
"""Stop long running docker images."""

import datetime
from collections.abc import Callable
from typing import Any

import dateparser
import dateutil.parser
import docker
import docker.errors
import requests.exceptions

from dockertidy.config import SingleConfig
from dockertidy.logger import SingleLog


class AutoStop:
    """AutoStop object to handle long running containers."""

    def __init__(self) -> None:
        self.config = SingleConfig()
        self.log = SingleLog()
        self.logger = SingleLog().logger
        self.docker = self._get_docker_client()

    def stop_containers(self) -> None:
        """Identify long running containers and terminate them."""
        client = self.docker
        config = self.config.config

        max_run_time = dateparser.parse(
            config["stop"]["max_run_time"],
            settings={"TO_TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True},
        )

        if not max_run_time:
            return

        prefix = config["stop"]["prefix"]
        dry_run = config["dry_run"]

        matcher = self._build_container_matcher(prefix)

        self.logger.info(
            f"Stopping containers older than '{max_run_time.strftime('%Y-%m-%d, %H:%M:%S')}'"
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

    def _stop_container(self, client: Any, cid: str) -> None:
        try:
            client.stop(cid)
        except requests.exceptions.Timeout as e:
            self.logger.warning(f"Failed to stop container {cid}: {e!s}")
        except docker.errors.APIError as e:
            self.logger.warning(f"Error stopping {cid}: {e!s}")

    def _build_container_matcher(self, prefixes: list[str]) -> Callable[[str], bool]:
        def matcher(name: str) -> bool:
            return any(name.startswith(prefix) for prefix in prefixes)

        return matcher

    def _has_been_running_since(
        self, container: dict[str, Any], min_time: datetime.datetime | None
    ) -> bool:
        started_at = container.get("State", {}).get("StartedAt")
        if not started_at:
            return False

        if min_time is None:
            return True

        return dateutil.parser.parse(started_at) <= min_time

    def _get_docker_client(self) -> Any:
        config = self.config.config
        return docker.APIClient(version="auto", timeout=config["http_timeout"])

    def run(self) -> None:
        """AutoStop main method."""
        self.logger.info("Start autostop")
        config = self.config.config

        if config["stop"]["max_run_time"]:
            self.stop_containers()

        if not config["stop"]["max_run_time"]:
            self.logger.warning("Skipped, no arguments given")
