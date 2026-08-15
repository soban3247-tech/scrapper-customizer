from datetime import date
from decimal import Decimal

import requests

from job_assistant.models import SearchConfig
from job_assistant.scrapers import RemoteOkScraper, ScraperRegistry

from .fakes import FakeResponse, FakeSession


def test_remote_ok_uses_fallback_and_normalizes_matching_jobs() -> None:
    session = FakeSession(
        requests.ConnectionError("primary unavailable"),
        FakeResponse(
            [
                {"legal": "API terms"},
                {
                    "id": 99,
                    "position": "Python Developer",
                    "company": "Example Ltd",
                    "description": "Build Python APIs",
                    "location": "Worldwide",
                    "date": "2026-08-12",
                    "url": "https://remoteok.com/jobs/99",
                    "salary_min": 70000,
                    "salary_max": "90000",
                    "tags": ["Python", "Backend"],
                },
                {
                    "id": 100,
                    "position": "Product Designer",
                    "company": "Example Ltd",
                    "description": "Design products",
                    "url": "https://remoteok.com/jobs/100",
                },
            ]
        ),
    )

    result = RemoteOkScraper(session=session).search(
        SearchConfig(query="Python", sources=["Remote OK"])
    )

    assert len(session.calls) == 2
    assert len(result.jobs) == 1
    assert result.jobs[0].posted_date == date(2026, 8, 12)
    assert result.jobs[0].salary_min == Decimal("70000")
    assert result.jobs[0].salary_max == Decimal("90000")


def test_remote_ok_network_failure_is_isolated_by_registry() -> None:
    session = FakeSession(
        requests.ConnectionError("primary unavailable"),
        requests.ConnectionError("fallback unavailable"),
    )
    registry = ScraperRegistry([RemoteOkScraper(session=session)])

    result = registry.run_selected(
        SearchConfig(query="Python", sources=["Remote OK"])
    )[0]

    assert result.succeeded is False
    assert result.issues[0].code == "request_error"
    assert result.issues[0].retryable is True
    assert "fallback unavailable" not in result.issues[0].message
