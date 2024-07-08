#!/usr/bin/env python3
"""Remove unused docker containers and images."""

import fnmatch
from collections import namedtuple

import dateutil.parser
import docker
import docker.errors
import requests.exceptions

from dockertidy.config import SingleConfig
from dockertidy.logger import SingleLog
from dockertidy.parser import timedelta


class GarbageCollector:
    """Garbage collector object to handle cleanup tasks of container, images and volumes."""

    # This seems to be something docker uses for a null/zero date
    YEAR_ZERO = "0001-01-01T00:00:00Z"
    ExcludeLabel = namedtuple("ExcludeLabel", ["key", "value"])

    def __init__(self):
        self.config = SingleConfig()
        self.log = SingleLog()
        self.logger = SingleLog().logger
        self.docker = self._get_docker_client()

    def cleanup_containers(self):
        """Identify old containers and remove them."""
        config = self.config.config
        client = self.docker
        all_containers = self._get_all_containers()

        filtered_containers = self._filter_excluded_containers(all_containers)

        self.logger.info(
            "Removing containers older than '{}'".format(
                timedelta(config["gc"]["max_container_age"], dt_format="%Y-%m-%d, %H:%M:%S")
            )
        )

        for container_summary in reversed(list(filtered_containers)):
            container = self._api_call(
                client.inspect_container,
                container=container_summary["Id"],
            )
            if not container or not self._should_remove_container(
                container,
                timedelta(config["gc"]["max_container_age"]),
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

    def _filter_excluded_containers(self, containers):
        config = self.config.config

        if not config["gc"]["exclude_container_labels"]:
            return containers

        def include_container(container):
            return not self._should_exclude_container_with_labels(container)

        return filter(include_container, containers)

    def _should_exclude_container_with_labels(self, container):
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

    def _should_remove_container(self, container, min_date):
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

    def _get_all_containers(self):
        client = self.docker
        self.logger.info("Getting all containers")
        containers = client.containers(all=True)
        self.logger.info("Found %s containers", len(containers))
        return containers

    def _get_all_images(self):
        client = self.docker
        self.logger.info("Getting all images")
        images = client.images()
        self.logger.info("Found %s images", len(images))
        return images

    def _get_dangling_volumes(self):
        client = self.docker
        self.logger.info("Getting dangling volumes")
        volumes = client.volumes({"dangling": True})["Volumes"] or []
        self.logger.info("Found %s dangling volumes", len(volumes))
        return volumes

    def cleanup_images(self, exclude_set):
        """Identify old images and remove them."""
        # re-fetch container list so that we don't  include removed containers
        client = self.docker
        config = self.config.config

        containers = self._get_all_containers()
        images = self._get_all_images()
        if docker.utils.compare_version("1.21", client._version) < 0:
            image_tags_in_use = {container["Image"] for container in containers}
            images = self._filter_images_in_use(images, image_tags_in_use)
        else:
            # ImageID field was added in 1.21
            image_ids_in_use = {container["ImageID"] for container in containers}
            images = self._filter_images_in_use_by_id(images, image_ids_in_use)
        images = self._filter_excluded_images(images, exclude_set)

        self.logger.info(
            "Removing images older than '{}'".format(
                timedelta(config["gc"]["max_image_age"], dt_format="%Y-%m-%d, %H:%M:%S")
            )
        )
        for image_summary in reversed(list(images)):
            self._remove_image(image_summary, timedelta(config["gc"]["max_image_age"]))

    def _filter_excluded_images(self, images, exclude_set):
        def include_image(image_summary):
            image_tags = image_summary.get("RepoTags")
            if self._no_image_tags(image_tags):
                return True
            for exclude_pattern in exclude_set:
                if fnmatch.filter(image_tags, exclude_pattern):
                    return False
            return True

        return filter(include_image, images)

    def _filter_images_in_use(self, images, image_tags_in_use):
        def get_tag_set(image_summary):
            image_tags = image_summary.get("RepoTags")
            if self._no_image_tags(image_tags):
                # The repr of the image Id used by client.containers()
                return {"{id}:latest".format(id=image_summary["Id"][:12])}
            return set(image_tags)

        def image_not_in_use(image_summary):
            return not get_tag_set(image_summary) & image_tags_in_use

        return filter(image_not_in_use, images)

    def _filter_images_in_use_by_id(self, images, image_ids_in_use):
        def image_not_in_use(image_summary):
            return image_summary["Id"] not in image_ids_in_use

        return filter(image_not_in_use, images)

    def _is_image_old(self, image, min_date):
        return dateutil.parser.parse(image["Created"]) < min_date

    def _no_image_tags(self, image_tags):
        return not image_tags or image_tags == ["<none>:<none>"]

    def _remove_image(self, image_summary, min_date):
        config = self.config.config
        client = self.docker
        image = self._api_call(client.inspect_image, image=image_summary["Id"])

        if not image or not self._is_image_old(image, min_date):
            return

        self.logger.info(f"Removing image {self._format_image(image, image_summary)}")
        if config["dry_run"]:
            return

        image_tags = image_summary.get("RepoTags")
        # If there are no tags, remove the id
        if self._no_image_tags(image_tags):
            self._api_call(client.remove_image, image=image_summary["Id"])
            return

        # Remove any repository tags so we don't  hit 409 Conflict
        for image_tag in image_tags:
            self._api_call(client.remove_image, image=image_tag)

    def _remove_volume(self, volume):
        config = self.config.config
        client = self.docker
        if not volume:
            return

        self.logger.info("Removing volume {name}".format(name=volume["Name"]))
        if config["dry_run"]:
            return

        self._api_call(client.remove_volume, name=volume["Name"])

    def cleanup_volumes(self):
        """Identify old volumes and remove them."""
        dangling_volumes = self._get_dangling_volumes()

        self.logger.info("Removing dangling volumes")
        for volume in reversed(dangling_volumes):
            self.logger.info("Removing dangling volume %s", volume["Name"])
            self._remove_volume(volume)

    def _api_call(self, func, **kwargs):
        try:
            return func(**kwargs)
        except requests.exceptions.Timeout as e:
            params = ",".join("%s=%s" % item for item in kwargs.items())  # noqa:UP031
            self.logger.warning(f"Failed to call {func.__name__} {params} {e!s}")
        except docker.errors.APIError as e:
            params = ",".join("%s=%s" % item for item in kwargs.items())  # noqa:UP031
            self.logger.warning(f"Error calling {func.__name__} {params} {e!s}")

    def _format_image(self, image, image_summary):
        def get_tags():
            tags = image_summary.get("RepoTags")
            if not tags or tags == ["<none>:<none>"]:
                return ""
            return ", ".join(tags)

        return "{id} {tags}".format(id=image["Id"][:16], tags=get_tags())

    def _build_exclude_set(self):
        config = self.config.config

        def is_image_tag(line):
            return line and not line.startswith("#")

        return set(config["gc"]["exclude_images"])

    def _format_exclude_labels(self):
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

    def _get_docker_client(self):
        config = self.config.config
        try:
            return docker.APIClient(version="auto", timeout=config["http_timeout"])
        except docker.errors.DockerException as e:
            self.log.sysexit_with_message(f"Can't create docker client\n{e}")

    def run(self):
        """Garbage collector main method."""
        self.logger.info("Start garbage collection")
        config = self.config.config
        self._format_exclude_labels()

        if config["gc"]["max_container_age"]:
            self.cleanup_containers()

        if config["gc"]["max_image_age"]:
            exclude_set = self._build_exclude_set()
            self.cleanup_images(exclude_set)

        if config["gc"]["dangling_volumes"]:
            self.cleanup_volumes()

        if (
            not config["gc"]["max_container_age"]
            and not config["gc"]["max_image_age"]
            and not config["gc"]["dangling_volumes"]
        ):
            self.logger.ing("Skipped, no arguments given")
