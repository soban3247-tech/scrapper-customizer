import pytest

from job_assistant.scrapers.errors import ScraperRequestError, ScraperResponseError
from job_assistant.scrapers.http import request_json

from .fakes import FakeResponse, FakeSession


def test_http_429_is_reported_as_retryable() -> None:
    session = FakeSession(FakeResponse({}, status_code=429))

    with pytest.raises(ScraperRequestError) as error:
        request_json(session, "https://example.com/jobs")

    assert error.value.retryable is True


def test_invalid_json_is_reported_as_response_error() -> None:
    session = FakeSession(FakeResponse(ValueError("not JSON")))

    with pytest.raises(ScraperResponseError, match="Invalid JSON"):
        request_json(session, "https://example.com/jobs")
