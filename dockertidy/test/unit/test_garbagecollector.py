"""Test GarbageCollector class."""

import docker
import pytest
import requests

from dockertidy import garbage_collector

pytest_plugins = [
    "dockertidy.test.fixtures.fixtures",
]


@pytest.fixture
def gc(mocker):
    mocker.patch.object(
        garbage_collector.GarbageCollector,
        "_get_docker_client",
        return_value=mocker.create_autospec(docker.APIClient)
    )

    gc = garbage_collector.GarbageCollector()
    return gc


def test_is_running(gc, container, now):
    container["State"]["Running"] = True

    assert not gc._should_remove_container(container, now)


def test_is_ghost(gc, container, now):
    container["State"]["Ghost"] = True

    assert gc._should_remove_container(container, now)


def test_old_never_run(gc, container, now, earlier_time):
    container["Created"] = str(earlier_time)
    container["State"]["FinishedAt"] = gc.YEAR_ZERO

    assert gc._should_remove_container(container, now)


def test_not_old_never_run(gc, container, now, earlier_time):
    container["Created"] = str(now)
    container["State"]["FinishedAt"] = gc.YEAR_ZERO

    assert not gc._should_remove_container(container, now)


def test_old_stopped(gc, container, now):
    assert gc._should_remove_container(container, now)


def test_not_old(gc, container, now):
    container["State"]["FinishedAt"] = "2014-01-21T00:00:00Z"

    assert not gc._should_remove_container(container, now)


def test_cleanup_containers(gc, mocker, containers):
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


def test_filter_excluded_containers(gc):
    containers = [
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


def test_cleanup_images(mocker, gc, containers):
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


def test_cleanup_volumes(mocker, gc):
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
    assert client.remove_volume.mock_calls == [
        mocker.call(name=volume["Name"]) for volume in reversed(volumes["Volumes"])
    ]


def test_filter_images_in_use(gc, images):
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


def test_filter_images_in_use_by_id(mocker, gc, containers):
    client = mocker.create_autospec(docker.APIClient)
    client._version = "1.21"
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


def test_filter_excluded_images(gc, images):
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


def test_filter_excluded_images_advanced(gc, images):
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


def test_is_image_old(gc, image, now):
    assert gc._is_image_old(image, now)


def test_is_image_old_false(gc, image, later_time):
    assert not gc._is_image_old(image, later_time)


def test_remove_image_no_tags(mocker, gc, image, now):
    client = mocker.create_autospec(docker.APIClient)
    image_id = "abcd"
    image_summary = {"Id": image_id}
    client.inspect_image.return_value = image

    gc.docker = client
    gc._remove_image(image_summary, now)
    client.remove_image.assert_called_once_with(image=image_id)


def test_remove_image_new_image_not_removed(mocker, gc, image, later_time):
    client = mocker.create_autospec(docker.APIClient)
    image_id = "abcd"
    image_summary = {"Id": image_id}
    client.inspect_image.return_value = image

    gc.docker = client
    gc._remove_image(image_summary, later_time)
    assert not client.remove_image.mock_calls


def test_remove_image_with_tags(mocker, gc, image, now):
    client = mocker.create_autospec(docker.APIClient)
    image_id = "abcd"
    repo_tags = ["user/one:latest", "user/one:12345"]
    image_summary = {"Id": image_id, "RepoTags": repo_tags}
    client.inspect_image.return_value = image

    gc.docker = client
    gc._remove_image(image_summary, now)
    assert client.remove_image.mock_calls == [mocker.call(image=tag) for tag in repo_tags]


def test_api_call_success(mocker, gc):
    func = mocker.Mock()
    container = "abcd"
    result = gc._api_call(func, container=container)
    func.assert_called_once_with(container="abcd")

    assert result == func.return_value


def test_api_call_with_timeout(mocker, gc):
    func = mocker.Mock(side_effect=requests.exceptions.ReadTimeout("msg"), __name__="remove_image")
    image = "abcd"

    mock_log = mocker.patch.object(gc, "logger", autospec=True)
    gc._api_call(func, image=image)

    func.assert_called_once_with(image="abcd")
    mock_log.warning.assert_called_once_with("Failed to call remove_image " + "image=abcd msg")


def test_api_call_with_api_error(mocker, gc):
    func = mocker.Mock(
        side_effect=docker.errors.APIError(
            "Ooops",
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


def test_get_all_containers(mocker, gc):
    client = mocker.create_autospec(docker.APIClient)
    count = 10
    client.containers.return_value = [mocker.Mock() for _ in range(count)]

    mock_log = mocker.patch.object(gc, "logger", autospec=True)

    gc.docker = client
    containers = gc._get_all_containers()
    assert containers == client.containers.return_value
    client.containers.assert_called_once_with(all=True)
    mock_log.info.assert_called_with("Found %s containers", count)


def test_get_all_images(mocker, gc):
    client = mocker.create_autospec(docker.APIClient)
    count = 7
    client.images.return_value = [mocker.Mock() for _ in range(count)]

    mock_log = mocker.patch.object(gc, "logger", autospec=True)

    gc.docker = client
    images = gc._get_all_images()
    assert images == client.images.return_value
    mock_log.info.assert_called_with("Found %s images", count)


def test_get_dangling_volumes(mocker, gc):
    client = mocker.create_autospec(docker.APIClient)
    count = 4
    client.volumes.return_value = {"Volumes": [mocker.Mock() for _ in range(count)]}

    mock_log = mocker.patch.object(gc, "logger", autospec=True)

    gc.docker = client
    volumes = gc._get_dangling_volumes()
    assert volumes == client.volumes.return_value["Volumes"]
    mock_log.info.assert_called_with("Found %s dangling volumes", count)


def test_build_exclude_set(gc):
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


def test_format_exclude_labels(gc):
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


def test_build_exclude_set_empty(gc):
    gc.config.config["gc"]["exclude_images"] = []
    exclude_set = gc._build_exclude_set()
    assert exclude_set == set()


def test_get_docker_client(gc, mocker):
    assert isinstance(gc.docker, docker.APIClient)
