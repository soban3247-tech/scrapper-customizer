from datetime import date

from job_assistant.models import Job, SearchConfig
from job_assistant.scrapers import ScrapeResult
from job_assistant.search import SearchProgressStatus, run_search


class FakeRegistry:
    def __init__(self) -> None:
        self.seen_sources: list[str] = []

    def run_selected(self, config: SearchConfig) -> list[ScrapeResult]:
        source_id = config.sources[0]
        self.seen_sources.append(source_id)
        if source_id == "Broken Source":
            return [ScrapeResult.failure(source_id, "Temporary source failure")]
        return [
            ScrapeResult(
                source_id=source_id,
                jobs=[
                    Job(
                        source=source_id,
                        title="Python Developer",
                        company="Example",
                        posted_date=date(2026, 8, 12),
                        apply_url="https://example.com/jobs/python",
                    )
                ],
            )
        ]


def test_search_continues_after_one_source_fails_and_reports_progress() -> None:
    registry = FakeRegistry()
    progress = []
    config = SearchConfig(
        query="Python Developer",
        posted_after=date(2026, 8, 1),
        sources=["Broken Source", "Working Source"],
    )

    result = run_search(registry, config, on_progress=progress.append)  # type: ignore[arg-type]

    assert registry.seen_sources == ["Broken Source", "Working Source"]
    assert [job.source for job in result.jobs] == ["Working Source"]
    assert len(result.issues) == 1
    assert result.issues[0].fatal is True
    assert [event.status for event in progress] == [
        SearchProgressStatus.STARTED,
        SearchProgressStatus.FAILED,
        SearchProgressStatus.STARTED,
        SearchProgressStatus.COMPLETED,
    ]


def test_search_deduplicates_jobs_across_sources() -> None:
    registry = FakeRegistry()
    config = SearchConfig(
        query="Python",
        sources=["First", "Second"],
    )

    result = run_search(registry, config)  # type: ignore[arg-type]

    assert len(result.jobs) == 1
    assert len(result.source_results) == 2
