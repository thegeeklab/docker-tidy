"""Global pytest fixtures."""
# cspell:ignore abcdabcdabcdabcd,babababababaabababab,abbb,abcda

import datetime
from typing import Any

import pytest
from dateutil import tz


@pytest.fixture
def container() -> dict[str, Any]:
    return {
        "Id": "abcdabcdabcdabcd",
        "Created": "2013-12-20T17:00:00Z",
        "Name": "/container_name",
        "State": {
            "Running": False,
            "FinishedAt": "2014-01-01T17:30:00Z",
            "StartedAt": "2014-01-01T17:01:00Z",
        }
    }


@pytest.fixture
def containers()-> list[dict[str, Any]]:
    return [
        {
            "Id": "abcd",
            "Name": "one",
            "Created": "2014-01-01T01:01:01Z",
            "State": {
                "Running": False,
                "FinishedAt": "2014-01-01T01:01:01Z",
            },
        },
        {
            "Id": "abbb",
            "Name": "two",
            "Created": "2014-01-01T01:01:01Z",
            "State": {
                "Running": True,
                "FinishedAt": "2014-01-01T01:01:01Z",
            },
        },
    ]


@pytest.fixture
def image() -> dict[str, str]:
    return {
        "Id": "abcdabcdabcdabcd",
        "Created": "2014-01-20T05:00:00Z",
    }


@pytest.fixture
def images()-> list[dict[str, list[str]|str]]:
    return [
        {
            "RepoTags": ["<none>:<none>"],
            "Id": "2471708c19beabababab"
        },
        {
            "RepoTags": ["<none>:<none>"],
            "Id": "babababababaabababab"
        },
        {
            "RepoTags": ["user/one:latest", "user/one:abcd"]
        },
        {
            "RepoTags": ["other-1:abcda"]
        },
        {
            "RepoTags": ["other-2:abc45"]
        },
        {
            "RepoTags": ["new_image:latest", "new_image:123"]
        },
    ]


@pytest.fixture
def now() -> datetime.datetime:
    return datetime.datetime(2014, 1, 20, 10, 10, tzinfo=tz.tzutc())


@pytest.fixture
def earlier_time() -> datetime.datetime:
    return datetime.datetime(2014, 1, 1, 0, 0, tzinfo=tz.tzutc())


@pytest.fixture
def later_time() -> datetime.datetime:
    return datetime.datetime(2014, 1, 20, 0, 10, tzinfo=tz.tzutc())
