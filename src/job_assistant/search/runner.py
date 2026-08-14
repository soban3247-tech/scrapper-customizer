"""Run selected scraper adapters with progress and failure isolation."""

from collections.abc import Callable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from job_assistant.models import Job, MatchResult, SearchConfig
from job_assistant.scrapers import (
    ScrapeResult,
    ScraperIssue,
    ScraperRegistry,
    deduplicate_jobs,
    filter_jobs_by_date,
)


class SearchProgressStatus(StrEnum):
    """Lifecycle states reported while one source is running."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchProgress(BaseModel):
    """A UI-safe progress event for one selected source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    source_number: int = Field(ge=1)
    source_count: int = Field(ge=1)
    status: SearchProgressStatus
    job_count: int = Field(default=0, ge=0)
    issue_count: int = Field(default=0, ge=0)


class SearchRunResult(BaseModel):
    """Combined output from a multi-source search."""

    model_config = ConfigDict(extra="forbid")

    jobs: list[Job] = Field(default_factory=list)
    matches: list[MatchResult] = Field(default_factory=list)
    issues: list[ScraperIssue] = Field(default_factory=list)
    source_results: list[ScrapeResult] = Field(default_factory=list)
    jobs_without_dates: int = Field(default=0, ge=0)


ProgressCallback = Callable[[SearchProgress], None]


def run_search(
    registry: ScraperRegistry,
    config: SearchConfig,
    *,
    on_progress: ProgressCallback | None = None,
) -> SearchRunResult:
    """Run sources one at a time while preserving every independent result."""

    source_results: list[ScrapeResult] = []
    source_count = len(config.sources)

    for source_number, source_id in enumerate(config.sources, start=1):
        _notify(
            on_progress,
            SearchProgress(
                source_id=source_id,
                source_number=source_number,
                source_count=source_count,
                status=SearchProgressStatus.STARTED,
            ),
        )

        source_config = config.model_copy(update={"sources": [source_id]})
        results = registry.run_selected(source_config)
        if len(results) != 1:
            result = ScrapeResult.failure(
                source_id,
                f"scraper '{source_id}' returned an invalid number of results",
                code="scraper_contract_error",
            )
        else:
            result = results[0]
        source_results.append(result)

        status = (
            SearchProgressStatus.COMPLETED
            if result.succeeded
            else SearchProgressStatus.FAILED
        )
        _notify(
            on_progress,
            SearchProgress(
                source_id=source_id,
                source_number=source_number,
                source_count=source_count,
                status=status,
                job_count=len(result.jobs),
                issue_count=len(result.issues),
            ),
        )

    jobs = deduplicate_jobs(
        job for source_result in source_results for job in source_result.jobs
    )
    jobs_without_dates = 0
    if config.posted_after is not None:
        jobs, jobs_without_dates = filter_jobs_by_date(jobs, config.posted_after)

    return SearchRunResult(
        jobs=jobs,
        issues=[
            issue
            for source_result in source_results
            for issue in source_result.issues
        ],
        source_results=source_results,
        jobs_without_dates=jobs_without_dates,
    )


def _notify(callback: ProgressCallback | None, event: SearchProgress) -> None:
    if callback is not None:
        callback(event)
