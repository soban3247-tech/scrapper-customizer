from datetime import date

import pytest

from job_assistant.models import JobSource, SearchConfig
from job_assistant.scrapers import RemotiveScraper, ScraperResponseError

from .fakes import FakeResponse, FakeSession


def test_remotive_maps_jobs_to_shared_model_and_keeps_invalid_issue() -> None:
    session = FakeSession(
        FakeResponse(
            {
                "jobs": [
                    {
                        "id": 123,
                        "title": "Python Developer",
                        "company_name": "Example Ltd",
                        "candidate_required_location": "Worldwide",
                        "job_type": "full_time",
                        "publication_date": "2026-08-10T12:00:00Z",
                        "url": "https://remotive.com/jobs/123",
                        "description": "Build Python services",
                        "tags": ["Python", "API"],
                    },
                    {
                        "id": 456,
                        "title": "Missing URL",
                        "company_name": "Example Ltd",
                    },
                ]
            }
        )
    )

    result = RemotiveScraper(session=session).search(
        SearchConfig(query="Python", sources=[JobSource.REMOTIVE])
    )

    assert result.succeeded is True
    assert len(result.jobs) == 1
    assert result.jobs[0].source == "Remotive"
    assert result.jobs[0].source_job_id == "123"
    assert result.jobs[0].posted_date == date(2026, 8, 10)
    assert result.jobs[0].tags == ["Python", "API"]
    assert result.issues[0].code == "invalid_job"
    assert session.calls[0]["params"] == {"search": "Python"}


def test_remotive_rejects_unexpected_response_shape() -> None:
    scraper = RemotiveScraper(session=FakeSession(FakeResponse({"data": []})))

    with pytest.raises(ScraperResponseError, match="jobs list"):
        scraper.search(SearchConfig(query="Python", sources=["Remotive"]))
