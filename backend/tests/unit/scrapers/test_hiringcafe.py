from datetime import date

from job_assistant.models import SearchConfig
from job_assistant.scrapers import HiringCafeScraper

from .fakes import FakeResponse, FakeSession


def homepage(build_id: str) -> FakeResponse:
    return FakeResponse(
        {},
        text=(
            '<html><script id="__NEXT_DATA__" type="application/json">'
            f'{{"buildId":"{build_id}"}}'
            "</script></html>"
        ),
        headers={"Content-Type": "text/html"},
    )


def test_hiringcafe_discovers_build_paginates_normalizes_and_deduplicates() -> None:
    raw_job = {
        "objectID": "hc-1",
        "job_information": {
            "title": "Python Engineer",
            "apply_url": "https://example.com/jobs/hc-1",
        },
        "v5_processed_job_data": {
            "company_name": "Example Ltd",
            "formatted_workplace_location": "Remote",
            "workplace_type": "Remote",
            "commitment": ["Full-time"],
            "date_posted": "2026-08-12",
            "yearly_min_compensation": 90000,
            "yearly_max_compensation": 120000,
        },
    }
    session = FakeSession(
        homepage("build-one"),
        FakeResponse(
            {"pageProps": {"ssrHits": [raw_job], "ssrIsLastPage": False}}
        ),
        FakeResponse(
            {"pageProps": {"ssrHits": [raw_job], "ssrIsLastPage": True}}
        ),
    )
    scraper = HiringCafeScraper(session=session, sleep=lambda _: None)

    result = scraper.search(
        SearchConfig(query="Python", sources=["HiringCafe"], max_pages=3)
    )

    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.source_job_id == "hc-1"
    assert job.title == "Python Engineer"
    assert job.company == "Example Ltd"
    assert job.location == "Remote"
    assert job.commitment == "Full-time"
    assert job.posted_date == date(2026, 8, 12)
    assert session.calls[1]["params"]["page"] == 0
    assert session.calls[2]["params"]["page"] == 1


def test_hiringcafe_refreshes_expired_build_id() -> None:
    session = FakeSession(
        homepage("old-build"),
        FakeResponse({}, status_code=404),
        homepage("new-build"),
        FakeResponse(
            {"pageProps": {"ssrHits": [], "ssrIsLastPage": True}}
        ),
    )

    result = HiringCafeScraper(session=session, sleep=lambda _: None).search(
        SearchConfig(query="Python", sources=["HiringCafe"])
    )

    assert result.jobs == []
    assert "new-build" in session.calls[3]["url"]


def test_hiringcafe_keeps_invalid_job_as_nonfatal_issue() -> None:
    session = FakeSession(
        homepage("build"),
        FakeResponse(
            {
                "pageProps": {
                    "ssrHits": [{"objectID": "invalid", "title": "No URL"}],
                    "ssrIsLastPage": True,
                }
            }
        ),
    )

    result = HiringCafeScraper(session=session, sleep=lambda _: None).search(
        SearchConfig(query="Python", sources=["HiringCafe"])
    )

    assert result.succeeded is True
    assert result.jobs == []
    assert result.issues[0].code == "invalid_job"
