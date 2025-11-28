"""Test Autostop class."""
# cspell:ignore asdb

import docker
import pytest
import datetime

from typing import Any
from dockertidy import autostop
from pytest_mock import MockFixture
pytest_plugins = [
    "dockertidy.test.fixtures.fixtures",
]


@pytest.fixture
def autostop_fixture(mocker: MockFixture) -> autostop.AutoStop:
    mocker.patch.object(
        autostop.AutoStop,
        "_get_docker_client",
        return_value=mocker.create_autospec(docker.APIClient)
    )

    stop = autostop.AutoStop()
    return stop


def test_stop_container(autostop_fixture: autostop.AutoStop, mocker: MockFixture) -> None:
    client = mocker.create_autospec(docker.APIClient)
    cid = "asdb"

    autostop_fixture._stop_container(client, cid)
    client.stop.assert_called_once_with(cid)


def test_build_container_matcher(autostop_fixture: autostop.AutoStop, mocker: MockFixture) -> None:
    prefixes = ["one_", "two_"]
    matcher = autostop_fixture._build_container_matcher(prefixes)

    assert matcher("one_container")
    assert matcher("two_container")
    assert not matcher("three_container")
    assert not matcher("one")


def test_has_been_running_since_true(autostop_fixture: autostop.AutoStop, container: dict[str, Any], later_time: datetime.datetime) -> None:
    assert autostop_fixture._has_been_running_since(container, later_time)


def test_has_been_running_since_false(autostop_fixture: autostop.AutoStop, container: dict[str, Any], earlier_time: datetime.datetime) -> None:
    assert not autostop_fixture._has_been_running_since(container, earlier_time)
