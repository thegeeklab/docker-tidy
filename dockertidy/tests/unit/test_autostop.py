"""Test Autostop class."""

import docker
import pytest

from dockertidy import Autostop

pytest_plugins = [
    "dockertidy.tests.fixtures.fixtures",
]


@pytest.fixture
def autostop(mocker):
    mocker.patch.object(
        Autostop.AutoStop,
        "_get_docker_client",
        return_value=mocker.create_autospec(docker.APIClient)
    )

    stop = Autostop.AutoStop()
    return stop


def test_stop_container(autostop, mocker):
    client = mocker.create_autospec(docker.APIClient)
    cid = "asdb"

    autostop._stop_container(client, cid)
    client.stop.assert_called_once_with(cid)


def test_build_container_matcher(autostop, mocker):
    prefixes = ["one_", "two_"]
    matcher = autostop._build_container_matcher(prefixes)

    assert matcher("one_container")
    assert matcher("two_container")
    assert not matcher("three_container")
    assert not matcher("one")


def test_has_been_running_since_true(autostop, container, later_time):
    assert autostop._has_been_running_since(container, later_time)


def test_has_been_running_since_false(autostop, container, earlier_time):
    assert not autostop._has_been_running_since(container, earlier_time)
