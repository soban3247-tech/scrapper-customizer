from datetime import date

from job_assistant.models import SearchConfig
from job_assistant.scrapers import GreenhouseScraper

from .fakes import FakeResponse, FakeSession


def test_greenhouse_keeps_successful_board_when_another_board_fails() -> None:
    session = FakeSession(
        FakeResponse({}, status_code=503),
        FakeResponse(
            {
                "jobs": [
                    {
                        "id": 42,
                        "title": "Python Engineer",
                        "content": "Build Python services",
                        "departments": [{"name": "Engineering"}],
                        "location": {"name": "Remote"},
                        "updated_at": "2026-08-12T10:30:00Z",
                        "absolute_url": "https://boards.greenhouse.io/good/jobs/42",
                    },
                    {
                        "id": 43,
                        "title": "Product Designer",
                        "content": "Design products",
                        "absolute_url": "https://boards.greenhouse.io/good/jobs/43",
                    },
                ]
            }
        ),
    )
    config = SearchConfig(
        query="Python",
        sources=["Greenhouse"],
        greenhouse_boards=["bad board", "good"],
    )

    result = GreenhouseScraper(session=session).search(config)

    assert result.succeeded is True
    assert len(result.jobs) == 1
    assert result.jobs[0].company == "good"
    assert result.jobs[0].location == "Remote"
    assert result.jobs[0].posted_date == date(2026, 8, 12)
    assert result.issues[0].code == "request_error"
    assert result.issues[0].retryable is True
    assert session.calls[0]["url"].endswith("/bad%20board/jobs")


def test_greenhouse_capabilities_describe_dynamic_board_input() -> None:
    field = GreenhouseScraper.capabilities.configuration_fields[0]

    assert field.key == "boards"
    assert field.required is True
