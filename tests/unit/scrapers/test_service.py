from datetime import date

from job_assistant.models import Job, SearchConfig
from job_assistant.scrapers import (
    ScrapeResult,
    ScraperCapabilities,
    ScraperRegistry,
    collect_jobs,
    filter_jobs_by_date,
)


def job(url: str, *, posted_date: date | None = None) -> Job:
    return Job(
        source="Test",
        title="Python Developer",
        company="Example Ltd",
        apply_url=url,
        posted_date=posted_date,
    )


class DuplicateScraper:
    capabilities = ScraperCapabilities()

    def __init__(self, source_id: str, result_job: Job) -> None:
        self.source_id = source_id
        self.display_name = source_id
        self.result_job = result_job

    def search(self, config: SearchConfig) -> ScrapeResult:
        return ScrapeResult(source_id=self.source_id, jobs=[self.result_job])


def test_collection_deduplicates_jobs_across_sources() -> None:
    duplicate = job("https://example.com/jobs/1")
    registry = ScraperRegistry(
        [DuplicateScraper("one", duplicate), DuplicateScraper("two", duplicate)]
    )

    jobs, issues = collect_jobs(
        registry,
        SearchConfig(query="Python", sources=["one", "two"]),
    )

    assert jobs == [duplicate]
    assert issues == []


def test_date_filter_counts_missing_and_excludes_future_or_old_jobs() -> None:
    inside = job("https://example.com/inside", posted_date=date(2026, 8, 10))
    old = job("https://example.com/old", posted_date=date(2026, 7, 1))
    future = job("https://example.com/future", posted_date=date(2026, 8, 14))
    missing = job("https://example.com/missing")

    filtered, missing_count = filter_jobs_by_date(
        [inside, old, future, missing],
        date(2026, 8, 1),
        today=date(2026, 8, 13),
    )

    assert filtered == [inside]
    assert missing_count == 1
