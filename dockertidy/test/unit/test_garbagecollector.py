"""Test GarbageCollector class."""
# cspell:ignore abcdabcdabcdabcd,babababababaabababab,abbb,abcda

import datetime
from collections import namedtuple

import docker
import pytest
import requests

from dockertidy import garbage_collector
from dockertidy.garbage_collector import parse_disk_size
from pytest_mock import MockFixture
from typing import Any

DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])

pytest_plugins = [
    "dockertidy.test.fixtures.fixtures",
]


@pytest.fixture
def gc(mocker: MockFixture) -> garbage_collector.GarbageCollector:
    mocker.patch.object(
        garbage_collector.GarbageCollector,
        "_get_docker_client",
        return_value=mocker.create_autospec(docker.APIClient)
    )

    gc = garbage_collector.GarbageCollector()
    return gc


def test_is_running(gc: garbage_collector.GarbageCollector, container: dict[str, Any], now: datetime.datetime) -> None:
    container["State"]["Running"] = True

    assert not gc._should_remove_container(container, now)


def test_is_ghost(gc: garbage_collector.GarbageCollector, container: dict[str, Any], now: datetime.datetime) -> None:
    container["State"]["Ghost"] = True

    assert gc._should_remove_container(container, now)


def test_old_never_run(gc: garbage_collector.GarbageCollector, container: dict[str, Any], now: datetime.datetime, earlier_time: datetime.datetime) -> None:
    container["Created"] = str(earlier_time)
    container["State"]["FinishedAt"] = gc.YEAR_ZERO

    assert gc._should_remove_container(container, now)


def test_not_old_never_run(gc: garbage_collector.GarbageCollector, container: dict[str, Any], now: datetime.datetime, earlier_time: datetime.datetime) -> None:
    container["Created"] = str(now)
    container["State"]["FinishedAt"] = gc.YEAR_ZERO

    assert not gc._should_remove_container(container, now)


def test_old_stopped(gc: garbage_collector.GarbageCollector, container: dict[str, Any], now: datetime.datetime) -> None:
    assert gc._should_remove_container(container, now)


def test_not_old(gc: garbage_collector.GarbageCollector, container: dict[str, Any], now: datetime.datetime) -> None:
    container["State"]["FinishedAt"] = "2014-01-21T00:00:00Z"

    assert not gc._should_remove_container(container, now)


def test_cleanup_containers(gc: garbage_collector.GarbageCollector, mocker: MockFixture, containers: list[dict[str, Any]]) -> None:
    client = mocker.create_autospec(docker.APIClient)
    client.containers.return_value = [
        {
            "Id": "abcd"
        },
        {
            "Id": "abbb"
        },
    ]
    client.inspect_container.side_effect = iter(containers)

    gc.config.config["gc"]["max_container_age"] = "0day"
    gc.docker = client
    gc.cleanup_containers()
    client.remove_container.assert_called_once_with(container="abcd", v=True)


def test_filter_excluded_containers(gc: garbage_collector.GarbageCollector) -> None:
    containers: list[dict[str, Any]] = [
        {
            "Labels": {
                "toot": ""
            }
        },
        {
            "Labels": {
                "too": "lol"
            }
        },
        {
            "Labels": {
                "toots": "lol"
            }
        },
        {
            "Labels": {
                "foo": "bar"
            }
        },
        {
            "Labels": None
        },
    ]

    result = gc._filter_excluded_containers(containers)
    assert containers == list(result)

    gc.config.config["gc"]["exclude_container_labels"] = [
        gc.ExcludeLabel(key="too", value=None),
        gc.ExcludeLabel(key="foo", value=None),
    ]
    result = gc._filter_excluded_containers(containers)
    assert [containers[0], containers[2], containers[4]] == list(result)

    gc.config.config["gc"]["exclude_container_labels"] = [
        gc.ExcludeLabel(key="too*", value="lol"),
    ]
    result = gc._filter_excluded_containers(containers)
    assert [containers[0], containers[3], containers[4]] == list(result)


def test_cleanup_images(mocker: MockFixture, gc: garbage_collector.GarbageCollector, containers: list[dict[str, Any]]) -> None:
    client = mocker.create_autospec(docker.APIClient)
    client._version = "1.21"
    client.images.return_value = images = [
        {
            "Id": "abcd"
        },
        {
            "Id": "abbb"
        },
    ]
    client.inspect_image.side_effect = iter(containers)

    gc.docker = client
    gc.config.config["gc"]["max_image_age"] = "0days"
    gc.cleanup_images(client)
    assert client.remove_image.mock_calls == [
        mocker.call(image=image["Id"]) for image in reversed(images)
    ]


def test_cleanup_volumes(mocker: MockFixture, gc: garbage_collector.GarbageCollector) -> None:
    client = mocker.create_autospec(docker.APIClient)
    client.volumes.return_value = volumes = {
        "Volumes": [
            {
                "Mountpoint": "unused",
                "Labels": None,
                "Driver": "unused",
                "Name": u"one"
            },
            {
                "Mountpoint": "unused",
                "Labels": None,
                "Driver": "unused",
                "Name": u"two"
            },
        ],
        "Warnings": None,
    }

    gc.docker = client
    gc.cleanup_volumes()
    assert volumes["Volumes"] is not None
    assert client.remove_volume.mock_calls == [
        mocker.call(name=volume["Name"]) for volume in reversed(volumes["Volumes"])
    ]


def test_filter_images_in_use(gc: garbage_collector.GarbageCollector, images: list[dict[str, list[str]|str]]) -> None:
    image_tags_in_use = set([
        "user/one:latest",
        "user/foo:latest",
        "other-2:abc45",
        "2471708c19be:latest",
    ])
    expected = [
        {
            "RepoTags": ["<none>:<none>"],
            "Id": "babababababaabababab"
        },
        {
            "RepoTags": ["other-1:abcda"]
        },
        {
            "RepoTags": ["new_image:latest", "new_image:123"]
        },
    ]

    actual = gc._filter_images_in_use(images, image_tags_in_use)
    assert list(actual) == expected


def test_filter_images_in_use_by_id(mocker: MockFixture, gc: garbage_collector.GarbageCollector, containers: list[dict[str, Any]]) -> None:
    client = mocker.create_autospec(docker.APIClient)
    client.api_version = "1.21"
    client.containers.return_value = [
        {
            "Id": "abcd",
            "ImageID": "1"
        },
        {
            "Id": "abbb",
            "ImageID": "2"
        },
    ]

    client.inspect_container.side_effect = iter(containers)
    client.images.return_value = [
        {
            "Id": "1",
            "Created": "2014-01-01T01:01:01Z"
        },
        {
            "Id": "2",
            "Created": "2014-01-01T01:01:01Z"
        },
        {
            "Id": "3",
            "Created": "2014-01-01T01:01:01Z"
        },
        {
            "Id": "4",
            "Created": "2014-01-01T01:01:01Z"
        },
        {
            "Id": "5",
            "Created": "2014-01-01T01:01:01Z"
        },
        {
            "Id": "6",
            "Created": "2014-01-01T01:01:01Z"
        },
    ]

    client.inspect_image.side_effect = lambda image: {
        "Id": image,
        "Created": "2014-01-01T01:01:01Z"
    }

    gc.docker = client
    gc.config.config["gc"]["max_image_age"] = "0days"
    gc.cleanup_images(set())
    assert client.remove_image.mock_calls == [
        mocker.call(image=id_) for id_ in ["6", "5", "4", "3"]
    ]


def test_filter_excluded_images(gc: garbage_collector.GarbageCollector, images: list[dict[str, list[str]|str]]) -> None:
    exclude_set = set([
        "user/one:latest",
        "user/foo:latest",
        "other-2:abc45",
    ])
    expected = [
        {
            "RepoTags": ["<none>:<none>"],
            "Id": "2471708c19beabababab"
        },
        {
            "RepoTags": ["<none>:<none>"],
            "Id": "babababababaabababab"
        },
        {
            "RepoTags": ["other-1:abcda"]
        },
        {
            "RepoTags": ["new_image:latest", "new_image:123"]
        },
    ]

    actual = gc._filter_excluded_images(images, exclude_set)
    assert list(actual) == expected


def test_filter_excluded_images_advanced(gc: garbage_collector.GarbageCollector, images: list[dict[str, list[str]|str]]) -> None:
    exclude_set = set([
        "user/one:*",
        "new_*:123",
        "other-1:abc*",
    ])
    expected = [
        {
            "RepoTags": ["<none>:<none>"],
            "Id": "2471708c19beabababab"
        },
        {
            "RepoTags": ["<none>:<none>"],
            "Id": "babababababaabababab"
        },
        {
            "RepoTags": ["other-2:abc45"]
        },
    ]

    actual = gc._filter_excluded_images(images, exclude_set)
    assert list(actual) == expected


def test_is_image_old(gc: garbage_collector.GarbageCollector, image: dict[str, str], now: datetime.datetime) -> None:
    assert gc._is_image_old(image, now)


def test_is_image_old_false(gc: garbage_collector.GarbageCollector, image: dict[str, str], later_time: datetime.datetime) -> None:
    assert not gc._is_image_old(image, later_time)


def test_remove_image_no_tags(mocker: MockFixture, gc: garbage_collector.GarbageCollector, image: dict[str, str], now: datetime.datetime) -> None:
    client = mocker.create_autospec(docker.APIClient)
    image_id = "abcd"
    image_summary = {"Id": image_id}
    client.inspect_image.return_value = image

    gc.docker = client
    gc._remove_image(image_summary, now)
    client.remove_image.assert_called_once_with(image=image_id)


def test_remove_image_new_image_not_removed(mocker: MockFixture, gc: garbage_collector.GarbageCollector, image: dict[str, str], later_time: datetime.datetime) -> None:
    client = mocker.create_autospec(docker.APIClient)
    image_id = "abcd"
    image_summary = {"Id": image_id}
    client.inspect_image.return_value = image

    gc.docker = client
    gc._remove_image(image_summary, later_time)
    assert not client.remove_image.mock_calls


def test_remove_image_with_tags(mocker: MockFixture, gc: garbage_collector.GarbageCollector, image: dict[str, str], now: datetime.datetime) -> None:
    client = mocker.create_autospec(docker.APIClient)
    image_id = "abcd"
    repo_tags = ["user/one:latest", "user/one:12345"]
    image_summary = {"Id": image_id, "RepoTags": repo_tags}
    client.inspect_image.return_value = image

    gc.docker = client
    gc._remove_image(image_summary, now)
    assert client.remove_image.mock_calls == [mocker.call(image=tag) for tag in repo_tags]


def test_api_call_success(mocker: MockFixture, gc: garbage_collector.GarbageCollector) -> None:
    func = mocker.Mock()
    container = "abcd"
    result = gc._api_call(func, container=container)
    func.assert_called_once_with(container="abcd")

    assert result == func.return_value


def test_api_call_with_timeout(mocker: MockFixture, gc: garbage_collector.GarbageCollector) -> None:
    func = mocker.Mock(side_effect=requests.exceptions.ReadTimeout("msg"), __name__="remove_image")
    image = "abcd"

    mock_log = mocker.patch.object(gc, "logger", autospec=True)
    gc._api_call(func, image=image)

    func.assert_called_once_with(image="abcd")
    mock_log.warning.assert_called_once_with("Failed to call remove_image " + "image=abcd msg")


def test_api_call_with_api_error(mocker: MockFixture, gc: garbage_collector.GarbageCollector) -> None:
    func = mocker.Mock(
        side_effect=docker.errors.APIError(
            "Error",
            mocker.Mock(status_code=409, reason="Conflict", url="dummy"),
            explanation="failed"
        ),
        __name__="remove_image"
    )
    image = "abcd"

    mock_log = mocker.patch.object(gc, "logger", autospec=True)
    gc._api_call(func, image=image)

    func.assert_called_once_with(image="abcd")
    mock_log.warning.assert_called_once_with(
        "Error calling remove_image image=abcd "
        '409 Client Error for dummy: Conflict ("failed")'
    )


def test_get_all_containers(mocker: MockFixture, gc: garbage_collector.GarbageCollector) -> None:
    client = mocker.create_autospec(docker.APIClient)
    count = 10
    client.containers.return_value = [mocker.Mock() for _ in range(count)]

    mock_log = mocker.patch.object(gc, "logger", autospec=True)

    gc.docker = client
    containers = gc._get_all_containers()
    assert containers == client.containers.return_value
    client.containers.assert_called_once_with(all=True)
    mock_log.info.assert_called_with("Found %s containers", count)


def test_get_all_images(mocker: MockFixture, gc: garbage_collector.GarbageCollector) -> None:
    client = mocker.create_autospec(docker.APIClient)
    count = 7
    client.images.return_value = [mocker.Mock() for _ in range(count)]

    mock_log = mocker.patch.object(gc, "logger", autospec=True)

    gc.docker = client
    images = gc._get_all_images()
    assert images == client.images.return_value
    mock_log.info.assert_called_with("Found %s images", count)


def test_get_dangling_volumes(mocker: MockFixture, gc: garbage_collector.GarbageCollector) -> None:
    client = mocker.create_autospec(docker.APIClient)
    count = 4
    client.volumes.return_value = {"Volumes": [mocker.Mock() for _ in range(count)]}

    mock_log = mocker.patch.object(gc, "logger", autospec=True)

    gc.docker = client
    volumes = gc._get_dangling_volumes()
    assert volumes == client.volumes.return_value["Volumes"]
    mock_log.info.assert_called_with("Found %s dangling volumes", count)


def test_build_exclude_set(gc: garbage_collector.GarbageCollector) -> None:
    gc.config.config["gc"]["exclude_images"] = [
        "some_image:latest",
        "repo/foo:12345",
        "duplicate:latest",
    ]
    expected = set([
        "some_image:latest",
        "repo/foo:12345",
        "duplicate:latest",
    ])

    exclude_set = gc._build_exclude_set()
    assert exclude_set == expected


def test_format_exclude_labels(gc: garbage_collector.GarbageCollector) -> None:
    gc.config.config["gc"]["exclude_container_labels"] = [
        "voo*",
        "doo=poo",
    ]
    expected = [
        gc.ExcludeLabel(key="voo*", value=None),
        gc.ExcludeLabel(key="doo", value="poo"),
    ]
    gc._format_exclude_labels()
    assert expected == gc.config.config["gc"]["exclude_container_labels"]


def test_build_exclude_set_empty(gc: garbage_collector.GarbageCollector) -> None:
    gc.config.config["gc"]["exclude_images"] = []
    exclude_set = gc._build_exclude_set()
    assert exclude_set == set()


def test_get_docker_client(gc: garbage_collector.GarbageCollector, mocker: MockFixture) -> None:
    assert isinstance(gc.docker, docker.APIClient)


def test_parse_disk_size_bytes() -> None:
    assert parse_disk_size("10GB") == (10 * 1024**3, False)
    assert parse_disk_size("500MB") == (500 * 1024**2, False)
    assert parse_disk_size("1TB") == (1024**4, False)
    assert parse_disk_size("100KB") == (100 * 1024, False)
    assert parse_disk_size("1024B") == (1024, False)
    assert parse_disk_size("2048") == (2048, False)
    assert parse_disk_size("1G") == (1024**3, False)
    assert parse_disk_size("1M") == (1024**2, False)
    assert parse_disk_size("1K") == (1024, False)
    assert parse_disk_size("1T") == (1024**4, False)


def test_parse_disk_size_percent() -> None:
    assert parse_disk_size("10%") == (10, True)
    assert parse_disk_size("50%") == (50, True)
    assert parse_disk_size("1%") == (1, True)
    assert parse_disk_size("100%") == (100, True)


def test_parse_disk_size_percent_invalid() -> None:
    with pytest.raises(ValueError, match="Percentage must be between 1 and 100"):
        parse_disk_size("0%")
    with pytest.raises(ValueError, match="Percentage must be between 1 and 100"):
        parse_disk_size("101%")
    with pytest.raises(ValueError, match="Percentage must be between 1 and 100"):
        parse_disk_size("200%")


def test_parse_disk_size_invalid() -> None:
    with pytest.raises(ValueError, match="Size must be positive"):
        parse_disk_size("0")
    with pytest.raises(ValueError, match="Size must be positive"):
        parse_disk_size("0GB")
    with pytest.raises(ValueError, match="Size must be positive"):
        parse_disk_size("-1GB")
    with pytest.raises(ValueError, match="Invalid size format"):
        parse_disk_size("abc")


def test_cleanup_images_by_space_already_free(
    mocker: MockFixture, gc: garbage_collector.GarbageCollector,
) -> None:
    client = mocker.create_autospec(docker.APIClient)
    usage = DiskUsage(total=100 * 1024**3, used=10 * 1024**3, free=90 * 1024**3)
    mocker.patch.object(gc, "_get_disk_usage", return_value=usage)

    gc.config.config["gc"]["min_free_disk_space"] = "1MB"
    gc.config.config["gc"]["disk_path"] = "/var/lib/docker"

    mock_log = mocker.patch.object(gc, "logger", autospec=True)
    gc.docker = client
    gc.cleanup_images_by_space(set())

    client.images.assert_not_called()
    mock_log.info.assert_called_once()
    assert "already above" in mock_log.info.call_args[0][0]


def test_cleanup_images_by_space_removes_oldest_first(
    mocker: MockFixture,
    gc: garbage_collector.GarbageCollector,
    images_by_age: list[dict[str, Any]],
) -> None:
    client = mocker.create_autospec(docker.APIClient)
    client._version = "1.21"
    client.containers.return_value = []
    client.images.return_value = list(images_by_age)
    inspect_image_returns = [
        {"Id": "img_newest", "Created": "2024-06-01T00:00:00Z"},
        {"Id": "img_mid", "Created": "2023-06-01T00:00:00Z"},
        {"Id": "img_oldest", "Created": "2022-06-01T00:00:00Z"},
        {"Id": "img_none", "Created": "2022-01-01T00:00:00Z"},
        {"Id": "img_none", "Created": "2022-01-01T00:00:00Z"},
    ]
    client.inspect_image.side_effect = iter(inspect_image_returns)

    usage_calls = [
        DiskUsage(total=100 * 1024**3, used=95 * 1024**3, free=5 * 1024**3),
        DiskUsage(total=100 * 1024**3, used=92 * 1024**3, free=8 * 1024**3),
        DiskUsage(total=100 * 1024**3, used=80 * 1024**3, free=20 * 1024**3),
    ]
    mocker.patch.object(gc, "_get_disk_usage", side_effect=usage_calls)

    gc.config.config["gc"]["min_free_disk_space"] = "10GB"
    gc.config.config["gc"]["disk_path"] = "/var/lib/docker"
    gc.docker = client

    gc.cleanup_images_by_space(set())

    remove_calls = client.remove_image.mock_calls
    assert len(remove_calls) == 1
    assert mocker.call(image="img_none") in remove_calls


def test_cleanup_images_by_space_dry_run(
    mocker: MockFixture,
    gc: garbage_collector.GarbageCollector,
    images_by_age: list[dict[str, Any]],
) -> None:
    client = mocker.create_autospec(docker.APIClient)
    client._version = "1.21"
    client.containers.return_value = []
    client.images.return_value = list(images_by_age)
    client.inspect_image.side_effect = lambda image: {
        "Id": image,
        "Created": next(
            img["Created"] for img in images_by_age if img["Id"] == image
        ),
    }

    usage = DiskUsage(total=100 * 1024**3, used=99 * 1024**3, free=1 * 1024**3)
    mocker.patch.object(gc, "_get_disk_usage", return_value=usage)

    gc.config.config["gc"]["min_free_disk_space"] = "10GB"
    gc.config.config["gc"]["disk_path"] = "/var/lib/docker"
    gc.config.config["dry_run"] = True
    gc.docker = client

    gc.cleanup_images_by_space(set())

    client.remove_image.assert_not_called()


def test_cleanup_images_by_space_no_images(
    mocker: MockFixture, gc: garbage_collector.GarbageCollector,
) -> None:
    client = mocker.create_autospec(docker.APIClient)
    client._version = "1.21"
    client.containers.return_value = []
    client.images.return_value = []

    usage = DiskUsage(total=100 * 1024**3, used=99 * 1024**3, free=1 * 1024**3)
    mocker.patch.object(gc, "_get_disk_usage", return_value=usage)

    gc.config.config["gc"]["min_free_disk_space"] = "10GB"
    gc.config.config["gc"]["disk_path"] = "/var/lib/docker"
    gc.docker = client

    gc.cleanup_images_by_space(set())

    client.remove_image.assert_not_called()


def test_cleanup_images_by_space_percentage(
    mocker: MockFixture,
    gc: garbage_collector.GarbageCollector,
    images_by_age: list[dict[str, Any]],
) -> None:
    client = mocker.MagicMock(spec=docker.APIClient)
    client.api_version = "1.21"
    client.containers.return_value = []
    client.images.return_value = list(images_by_age)

    inspect_image_returns = [
        {"Id": "img_newest", "Created": "2024-06-01T00:00:00Z"},
        {"Id": "img_mid", "Created": "2023-06-01T00:00:00Z"},
        {"Id": "img_oldest", "Created": "2022-06-01T00:00:00Z"},
        {"Id": "img_none", "Created": "2022-01-01T00:00:00Z"},
        {"Id": "img_none", "Created": "2022-01-01T00:00:00Z"},
    ]
    client.inspect_image.side_effect = iter(inspect_image_returns)

    usage_calls = [
        DiskUsage(total=100 * 1024**3, used=95 * 1024**3, free=5 * 1024**3),
        DiskUsage(total=100 * 1024**3, used=95 * 1024**3, free=5 * 1024**3),
        DiskUsage(total=100 * 1024**3, used=85 * 1024**3, free=15 * 1024**3),
    ]
    mocker.patch.object(gc, "_get_disk_usage", side_effect=usage_calls)

    gc.config.config["gc"]["min_free_disk_space"] = "10%"
    gc.config.config["gc"]["disk_path"] = "/var/lib/docker"
    gc.config.config["dry_run"] = False
    gc.docker = client

    gc.cleanup_images_by_space(set())

    assert len(client.remove_image.mock_calls) == 1
    assert mocker.call(image="img_none") in client.remove_image.mock_calls


def test_cleanup_images_by_space_with_excluded(
    mocker: MockFixture,
    gc: garbage_collector.GarbageCollector,
    images_by_age: list[dict[str, Any]],
) -> None:
    client = mocker.MagicMock(spec=docker.APIClient)
    client.api_version = "1.21"
    client.containers.return_value = []
    client.images.return_value = list(images_by_age)
    inspect_image_returns = [
        {"Id": "img_newest", "Created": "2024-06-01T00:00:00Z"},
        {"Id": "img_mid", "Created": "2023-06-01T00:00:00Z"},
        {"Id": "img_none", "Created": "2022-01-01T00:00:00Z"},
        {"Id": "img_none", "Created": "2022-01-01T00:00:00Z"},
        {"Id": "img_mid", "Created": "2023-06-01T00:00:00Z"},
        {"Id": "img_newest", "Created": "2024-06-01T00:00:00Z"},
    ]
    client.inspect_image.side_effect = iter(inspect_image_returns)

    usage = DiskUsage(total=100 * 1024**3, used=99 * 1024**3, free=1 * 1024**3)
    mocker.patch.object(gc, "_get_disk_usage", return_value=usage)

    gc.config.config["gc"]["min_free_disk_space"] = "100GB"
    gc.config.config["gc"]["disk_path"] = "/var/lib/docker"
    gc.config.config["dry_run"] = False
    gc.docker = client

    gc.cleanup_images_by_space({"app:oldest"})

    remove_calls = client.remove_image.mock_calls
    assert mocker.call(image="app:oldest") not in remove_calls
    assert mocker.call(image="img_none") in remove_calls
    assert mocker.call(image="app:mid") in remove_calls
    assert mocker.call(image="app:newest") in remove_calls
