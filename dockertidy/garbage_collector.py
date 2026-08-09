#!/usr/bin/env python3
"""Remove unused docker containers and images."""

import datetime
import fnmatch
import shutil
from collections import namedtuple
from collections.abc import Callable
from typing import Any

import dateparser
import dateutil.parser
import docker
import docker.errors
import docker.utils
import requests.exceptions

from dockertidy.config import SingleConfig
from dockertidy.logger import SingleLog

SIZE_UNITS: dict[str, int] = {
    "B": 1,
    "K": 1024,
    "KB": 1024,
    "M": 1024**2,
    "MB": 1024**2,
    "G": 1024**3,
    "GB": 1024**3,
    "T": 1024**4,
    "TB": 1024**4,
}


def parse_disk_size(value: str) -> tuple[int, bool]:
    """
    Parse a disk space string like '10GB' or '15%'.

    Returns (bytes, is_percentage).
    """
    value = value.strip().upper()
    if value.endswith("%"):
        try:
            percent = int(value[:-1])
        except ValueError as e:
            raise ValueError(f"Invalid percentage format: '{value}'") from e
        if not 1 <= percent <= 100:
            raise ValueError(f"Percentage must be between 1 and 100, got {percent}%")
        return (percent, True)
    for unit, multiplier in sorted(SIZE_UNITS.items(), key=lambda x: len(x[0]), reverse=True):
        if value.endswith(unit) and len(unit) > 0 and value != unit:
            try:
                number = int(value[: -len(unit)])
            except ValueError as e:
                raise ValueError(f"Invalid size format: '{value}'") from e
            if number <= 0:
                raise ValueError(f"Size must be positive, got '{value}'")
            return (number * multiplier, False)
    try:
        bytes_value = int(value)
    except ValueError as e:
        raise ValueError(f"Invalid size format: '{value}'") from e
    if bytes_value <= 0:
        raise ValueError(f"Size must be positive, got '{value}'")
    return (bytes_value, False)


class GarbageCollector:
    """Garbage collector object to handle cleanup tasks of container, images and volumes."""

    # This seems to be something docker uses for a null/zero date
    YEAR_ZERO = "0001-01-01T00:00:00Z"
    ExcludeLabel = namedtuple("ExcludeLabel", ["key", "value"])

    def __init__(self) -> None:
        self.config = SingleConfig()
        self.log = SingleLog()
        self.logger = SingleLog().logger
        self.docker = self._get_docker_client()

    def cleanup_containers(self) -> None:
        """Identify old containers and remove them."""
        config = self.config.config
        client = self.docker
        all_containers = self._get_all_containers()

        filtered_containers = self._filter_excluded_containers(all_containers)

        max_container_age = dateparser.parse(
            config["gc"]["max_container_age"],
            settings={"TO_TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True},
        )

        if not max_container_age:
            return

        self.logger.info(
            f"Removing containers older than '{max_container_age.strftime('%Y-%m-%d, %H:%M:%S')}'"
        )

        for container_summary in reversed(list(filtered_containers)):
            container = self._api_call(
                client.inspect_container,
                container=container_summary["Id"],
            )
            if not container or not self._should_remove_container(
                container,
                max_container_age,
            ):
                continue

            self.logger.info(
                "Removing container {} {} {}".format(
                    container["Id"][:16],
                    container.get("Name", "").lstrip("/"),
                    container["State"]["FinishedAt"],
                )
            )

            if not config["dry_run"]:
                self._api_call(
                    client.remove_container,
                    container=container["Id"],
                    v=True,
                )

    def _filter_excluded_containers(
        self, containers: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        config = self.config.config

        if not config["gc"]["exclude_container_labels"]:
            return containers

        def include_container(container: dict[str, Any]) -> bool:
            return not self._should_exclude_container_with_labels(container)

        return list(filter(include_container, containers))

    def _should_exclude_container_with_labels(self, container: dict[str, Any]) -> bool:
        config = self.config.config

        if container["Labels"]:
            for exclude_label in config["gc"]["exclude_container_labels"]:
                if exclude_label.value:
                    matching_keys = fnmatch.filter(
                        container["Labels"].keys(),
                        exclude_label.key,
                    )
                    label_values_to_check = [
                        container["Labels"][matching_key] for matching_key in matching_keys
                    ]
                    if fnmatch.filter(label_values_to_check, exclude_label.value):
                        return True
                else:
                    if fnmatch.filter(container["Labels"].keys(), exclude_label.key):
                        return True
        return False

    def _should_remove_container(
        self, container: dict[str, Any], min_date: datetime.datetime
    ) -> bool:
        state = container.get("State", {})

        if state.get("Running"):
            return False

        if state.get("Ghost"):
            return True

        # Container was created, but never started
        if state.get("FinishedAt") == self.YEAR_ZERO:
            created_date = dateutil.parser.parse(container["Created"])
            return created_date < min_date

        finished_date = dateutil.parser.parse(state["FinishedAt"])
        return finished_date < min_date

    def _get_all_containers(self) -> Any:
        client = self.docker
        self.logger.info("Getting all containers")
        containers = client.containers(all=True)
        self.logger.info("Found %s containers", len(containers))
        return containers

    def _get_all_images(self) -> Any:
        client = self.docker
        self.logger.info("Getting all images")
        images = client.images()
        self.logger.info("Found %s images", len(images))
        return images

    def _get_dangling_volumes(self) -> list[dict[str, Any]]:
        client = self.docker
        self.logger.info("Getting dangling volumes")
        volumes = client.volumes({"dangling": True})["Volumes"] or []
        self.logger.info("Found %s dangling volumes", len(volumes))
        return volumes

    def _get_removable_images(self, exclude_set: set[str]) -> list[dict[str, Any]]:
        client = self.docker
        containers = self._get_all_containers()
        images = self._get_all_images()
        if docker.utils.compare_version("1.21", client.api_version) < 0:
            image_tags_in_use = {container.get("Image", "") for container in containers}
            images = self._filter_images_in_use(images, image_tags_in_use)
        else:
            image_ids_in_use = {container.get("ImageID", "") for container in containers}
            images = self._filter_images_in_use_by_id(images, image_ids_in_use)
        return self._filter_excluded_images(images, exclude_set)

    def cleanup_images(self, exclude_set: set[str]) -> None:
        """Identify old images and remove them."""
        config = self.config.config

        images = self._get_removable_images(exclude_set)

        max_image_age = dateparser.parse(
            config["gc"]["max_image_age"],
            settings={"TO_TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True},
        )

        if not max_image_age:
            return

        self.logger.info(
            f"Removing images older than '{max_image_age.strftime('%Y-%m-%d, %H:%M:%S')}'"
        )
        for image_summary in reversed(list(images)):
            self._remove_image(image_summary, max_image_age)

    def _filter_excluded_images(
        self, images: list[dict[str, Any]], exclude_set: set[str]
    ) -> list[dict[str, Any]]:
        def include_image(image_summary: dict[str, Any]) -> bool:
            image_tags = image_summary.get("RepoTags", [])
            if self._no_image_tags(image_tags):
                return True
            for exclude_pattern in exclude_set:
                if fnmatch.filter(image_tags, exclude_pattern):
                    return False
            return True

        return list(filter(include_image, images))

    def _filter_images_in_use(
        self, images: list[dict[str, Any]], image_tags_in_use: set[str]
    ) -> list[dict[str, Any]]:
        def get_tag_set(image_summary: dict[str, Any]) -> set[str]:
            image_tags = image_summary.get("RepoTags", [])
            if self._no_image_tags(image_tags):
                # The repr of the image Id used by client.containers()
                return {"{id}:latest".format(id=image_summary["Id"][:12])}
            return set(image_tags)

        def image_not_in_use(image_summary: dict[str, Any]) -> bool:
            return not get_tag_set(image_summary) & image_tags_in_use

        return list(filter(image_not_in_use, images))

    def _filter_images_in_use_by_id(
        self, images: list[dict[str, Any]], image_ids_in_use: set[str]
    ) -> list[dict[str, Any]]:
        def image_not_in_use(image_summary: dict[str, Any]) -> bool:
            return image_summary["Id"] not in image_ids_in_use

        return list(filter(image_not_in_use, images))

    def _is_image_old(self, image: dict[str, Any], min_date: datetime.datetime) -> bool:
        return dateutil.parser.parse(image["Created"]) < min_date

    def _no_image_tags(self, image_tags: list[str] | None) -> bool:
        return not image_tags or image_tags == ["<none>:<none>"]

    def _remove_image_tags(self, image_summary: dict[str, Any]) -> None:
        client = self.docker
        image_tags = image_summary.get("RepoTags", [])
        if self._no_image_tags(image_tags):
            self._api_call(client.remove_image, image=image_summary["Id"])
        else:
            for image_tag in image_tags:
                self._api_call(client.remove_image, image=image_tag)

    def _remove_image(self, image_summary: dict[str, Any], min_date: Any) -> None:
        config = self.config.config
        client = self.docker
        image = self._api_call(client.inspect_image, image=image_summary["Id"])

        if not image or not self._is_image_old(image, min_date):
            return

        self.logger.info(f"Removing image {self._format_image(image, image_summary)}")
        if config["dry_run"]:
            return

        self._remove_image_tags(image_summary)

    def _remove_volume(self, volume: dict[str, Any]) -> None:
        config = self.config.config
        client = self.docker
        if not volume:
            return

        self.logger.info("Removing volume {name}".format(name=volume["Name"]))
        if config["dry_run"]:
            return

        self._api_call(client.remove_volume, name=volume["Name"])

    def cleanup_volumes(self) -> None:
        """Identify old volumes and remove them."""
        dangling_volumes = self._get_dangling_volumes()

        self.logger.info("Removing dangling volumes")
        for volume in reversed(dangling_volumes):
            self.logger.info("Removing dangling volume %s", volume["Name"])
            self._remove_volume(volume)

    def _api_call(self, func: Callable[..., str | None], **kwargs: Any) -> Any:
        try:
            return func(**kwargs)
        except requests.exceptions.Timeout as e:
            params = ",".join("%s=%s" % item for item in kwargs.items())  # noqa:UP031
            self.logger.warning(f"Failed to call {func.__name__} {params} {e!s}")
        except docker.errors.APIError as e:
            params = ",".join("%s=%s" % item for item in kwargs.items())  # noqa:UP031
            self.logger.warning(f"Error calling {func.__name__} {params} {e!s}")

    def _format_image(self, image: dict[str, Any], image_summary: dict[str, Any]) -> str:
        def get_tags() -> str:
            tags = image_summary.get("RepoTags")
            if not tags or tags == ["<none>:<none>"]:
                return ""
            return ", ".join(tags)

        return "{id} {tags}".format(id=image["Id"][:16], tags=get_tags())

    def _build_exclude_set(self) -> set[str]:
        config = self.config.config

        def is_image_tag(line: str) -> bool:
            return bool(line) and not line.startswith("#")

        return set(config["gc"]["exclude_images"])

    def _format_exclude_labels(self) -> None:
        config = self.config.config
        exclude_labels = []

        for exclude_label_arg in config["gc"]["exclude_container_labels"]:
            split_exclude_label = exclude_label_arg.split("=", 1)
            exclude_label_key = split_exclude_label[0]
            exclude_label_value = split_exclude_label[1] if len(split_exclude_label) == 2 else None
            exclude_labels.append(
                self.ExcludeLabel(
                    key=exclude_label_key,
                    value=exclude_label_value,
                )
            )
        config["gc"]["exclude_container_labels"] = exclude_labels

    def _get_docker_client(self) -> docker.APIClient:
        config = self.config.config
        try:
            return docker.APIClient(version="auto", timeout=config["http_timeout"])
        except docker.errors.DockerException as e:
            self.log.sysexit_with_message(f"Can't create docker client\n{e}")

    def _get_disk_usage(self, path: str) -> Any:
        try:
            return shutil.disk_usage(path)
        except OSError as e:
            self.log.sysexit_with_message(f"Cannot check disk space at '{path}': {e}")

    def cleanup_images_by_space(self, exclude_set: set[str]) -> None:
        """Remove oldest images until the target free disk space is reached."""
        config = self.config.config
        client = self.docker

        try:
            target_value, is_percent = parse_disk_size(config["gc"]["min_free_disk_space"])
        except ValueError as e:
            self.log.sysexit_with_message(str(e))
        disk_path = config["gc"]["disk_path"]

        usage = self._get_disk_usage(disk_path)

        target_bytes = int(usage.total * (target_value / 100.0)) if is_percent else target_value

        if usage.free >= target_bytes:
            self.logger.info(
                f"Free disk space ({usage.free / 1024**3:.1f}GB) already above "
                f"target ({target_bytes / 1024**3:.1f}GB), skipping image cleanup by space"
            )
            return

        self.logger.info(
            f"Target: {target_bytes / 1024**3:.1f}GB free, "
            f"current: {usage.free / 1024**3:.1f}GB free, "
            f"removing oldest images until target is reached"
        )

        images = self._get_removable_images(exclude_set)

        decorated: list[tuple[dict[str, Any], dict[str, Any] | None, datetime.datetime]] = []
        for image_summary in images:
            image = self._api_call(client.inspect_image, image=image_summary["Id"])
            if image:
                created = dateutil.parser.parse(image["Created"])
            else:
                created = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
            decorated.append((image_summary, image, created))

        decorated.sort(key=lambda x: x[2])

        for image_summary, image, _ in decorated:
            current_usage = self._get_disk_usage(disk_path)
            if current_usage.free >= target_bytes:
                self.logger.info(
                    f"Reached target free space: {current_usage.free / 1024**3:.1f}GB free"
                )
                break

            if not image:
                continue

            self.logger.info(f"Removing image {self._format_image(image, image_summary)}")
            if config["dry_run"]:
                continue

            self._remove_image_tags(image_summary)

    def run(self) -> None:
        """Garbage collector main method."""
        self.logger.info("Start garbage collection")
        config = self.config.config
        self._format_exclude_labels()

        exclude_set = self._build_exclude_set()

        if config["gc"]["max_container_age"]:
            self.cleanup_containers()

        if config["gc"]["max_image_age"]:
            self.cleanup_images(exclude_set)

        if config["gc"]["min_free_disk_space"]:
            self.cleanup_images_by_space(exclude_set)

        if config["gc"]["dangling_volumes"]:
            self.cleanup_volumes()

        if (
            not config["gc"]["max_container_age"]
            and not config["gc"]["max_image_age"]
            and not config["gc"]["dangling_volumes"]
            and not config["gc"]["min_free_disk_space"]
        ):
            self.logger.warning("Skipped, no arguments given")
