from datetime import date

from job_assistant.models import SearchConfig
from job_assistant.scrapers import LeverScraper

from .fakes import FakeResponse, FakeSession


def test_lever_uses_generic_company_options_and_normalizes_jobs() -> None:
    session = FakeSession(
        FakeResponse(
            [
                {
                    "id": "lever-1",
                    "text": "Senior Python Engineer",
                    "descriptionPlain": "Build Python APIs",
                    "createdAt": 1786320000000,
                    "categories": {
                        "location": "Remote",
                        "commitment": "Full-time",
                    },
                    "lists": [{"text": "Backend"}],
                    "hostedUrl": "https://jobs.lever.co/example/lever-1",
                },
                {
                    "id": "lever-2",
                    "text": "Product Designer",
                    "descriptionPlain": "Design products",
                    "hostedUrl": "https://jobs.lever.co/example/lever-2",
                },
            ]
        )
    )
    config = SearchConfig(
        query="Python",
        sources=["Lever"],
        source_options={"Lever": {"companies": ["example"]}},
    )

    result = LeverScraper(session=session).search(config)

    assert len(result.jobs) == 1
    assert result.jobs[0].source_job_id == "lever-1"
    assert result.jobs[0].company == "example"
    assert result.jobs[0].location == "Remote"
    assert result.jobs[0].commitment == "Full-time"
    assert result.jobs[0].posted_date == date(2026, 8, 10)
    assert session.calls[0]["params"] == {"mode": "json"}


def test_lever_capabilities_describe_dynamic_company_input() -> None:
    field = LeverScraper.capabilities.configuration_fields[0]

    assert field.key == "companies"
    assert field.required is True
