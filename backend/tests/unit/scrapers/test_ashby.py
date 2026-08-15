from datetime import date
from decimal import Decimal

from job_assistant.models import SearchConfig
from job_assistant.scrapers import AshbyScraper, ScraperRegistry

from .fakes import FakeResponse, FakeSession


def test_ashby_normalizes_nested_location_department_and_compensation() -> None:
    session = FakeSession(
        FakeResponse(
            {
                "jobs": [
                    {
                        "id": "ashby-1",
                        "title": "Python Platform Engineer",
                        "descriptionPlain": "Build Python infrastructure",
                        "location": {"name": "Remote"},
                        "department": {"name": "Engineering"},
                        "publishedAt": "2026-08-11T08:00:00Z",
                        "jobUrl": "https://jobs.ashbyhq.com/example/ashby-1",
                        "compensation": {
                            "minValue": 80000,
                            "maxValue": "120000",
                            "currencyCode": "usd",
                        },
                    }
                ]
            }
        )
    )
    config = SearchConfig(
        query="Python",
        sources=["Ashby"],
        ashby_organizations=["example"],
    )

    result = AshbyScraper(session=session).search(config)

    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.location == "Remote"
    assert job.commitment == "Engineering"
    assert job.posted_date == date(2026, 8, 11)
    assert job.salary_min == Decimal("80000")
    assert job.salary_max == Decimal("120000")
    assert job.salary_currency == "USD"
    assert session.calls[0]["params"] == {"includeCompensation": "true"}


def test_all_ashby_target_failures_are_isolated_by_registry() -> None:
    session = FakeSession(FakeResponse({"unexpected": []}))
    registry = ScraperRegistry([AshbyScraper(session=session)])
    config = SearchConfig(
        query="Python",
        sources=["Ashby"],
        ashby_organizations=["broken"],
    )

    result = registry.run_selected(config)[0]

    assert result.succeeded is False
    assert result.issues[0].code == "response_error"


def test_ashby_capabilities_describe_dynamic_organization_input() -> None:
    field = AshbyScraper.capabilities.configuration_fields[0]

    assert field.key == "organizations"
    assert field.required is True
