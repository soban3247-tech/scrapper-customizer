from datetime import date

import pytest

from job_assistant.models import SearchConfig
from job_assistant.scrapers import ArbeitnowScraper, ScraperResponseError

from .fakes import FakeResponse, FakeSession


def test_arbeitnow_filters_query_and_follows_pagination() -> None:
    session = FakeSession(
        FakeResponse(
            {
                "data": [
                    {
                        "slug": "python-one",
                        "title": "Python Developer",
                        "company_name": "Alpha",
                        "description": "Build APIs",
                        "location": "Berlin",
                        "remote": True,
                        "job_types": ["full_time"],
                        "created_at": 1786320000,
                        "url": "https://arbeitnow.com/jobs/python-one",
                        "tags": ["Python"],
                    },
                    {
                        "slug": "designer",
                        "title": "Product Designer",
                        "company_name": "Alpha",
                        "description": "Design interfaces",
                        "url": "https://arbeitnow.com/jobs/designer",
                    },
                ],
                "links": {"next": "page-2"},
            }
        ),
        FakeResponse(
            {
                "data": [
                    {
                        "id": 2,
                        "title": "Senior Python Engineer",
                        "company_name": "Beta",
                        "description": "Python platform work",
                        "location": "Remote",
                        "remote": True,
                        "created_at": "2026-08-11T09:30:00Z",
                        "url": "https://arbeitnow.com/jobs/python-two",
                    }
                ],
                "links": {"next": "page-3"},
            }
        ),
    )

    result = ArbeitnowScraper(session=session).search(
        SearchConfig(query="Python", sources=["Arbeitnow"], max_pages=2)
    )

    assert [job.company for job in result.jobs] == ["Alpha", "Beta"]
    assert result.jobs[0].commitment == "full_time"
    assert result.jobs[0].posted_date == date(2026, 8, 10)
    assert [call["params"] for call in session.calls] == [{"page": 1}, {"page": 2}]


def test_arbeitnow_rejects_unexpected_response_shape() -> None:
    scraper = ArbeitnowScraper(session=FakeSession(FakeResponse({"data": {}})))

    with pytest.raises(ScraperResponseError, match="data list"):
        scraper.search(SearchConfig(query="Python", sources=["Arbeitnow"]))

