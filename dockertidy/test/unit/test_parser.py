import pytest
from datetime import datetime
import dateparser
from dockertidy.parser import timedelta

@pytest.mark.parametrize(
    "value,dt_format,expected_type",
    [
        ("1 day ago", None, datetime),
        ("2 hours ago", None, datetime),
        ("30 minutes ago", None, datetime),
        ("1 week ago", "%Y-%m-%d", str),
        ("2 months ago", "%Y-%m", str),
    ],
)
def test_timedelta(value, dt_format, expected_type):
    """Test timedelta function with various inputs."""
    result = timedelta(value, dt_format)
    assert isinstance(result, expected_type)
    if expected_type is str:
        assert datetime.strptime(result, dt_format)
    elif expected_type is datetime:
        assert result.tzinfo is not None

def test_timedelta_invalid():
    """Test that invalid time strings return None."""
    assert timedelta("invalid time string") is None
