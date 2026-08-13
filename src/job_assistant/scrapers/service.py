"""Cross-source collection, deduplication, and date filtering."""

from datetime import date
from collections.abc import Iterable

from job_assistant.models import Job, SearchConfig

from .base import ScraperIssue
from .registry import ScraperRegistry


def collect_jobs(
    registry: ScraperRegistry,
    config: SearchConfig,
) -> tuple[list[Job], list[ScraperIssue]]:
    """Run selected sources and combine their successful normalized jobs."""

    results = registry.run_selected(config)
    jobs = deduplicate_jobs(job for result in results for job in result.jobs)
    issues = [issue for result in results for issue in result.issues]
    return jobs, issues


def filter_jobs_by_date(
    jobs: list[Job],
    start_date: date,
    *,
    today: date | None = None,
) -> tuple[list[Job], int]:
    """Keep dated jobs in the inclusive range and count jobs without dates."""

    upper_bound = today or date.today()
    filtered: list[Job] = []
    missing_date_count = 0
    for job in jobs:
        if job.posted_date is None:
            missing_date_count += 1
        elif start_date <= job.posted_date <= upper_bound:
            filtered.append(job)
    return filtered, missing_date_count


def deduplicate_jobs(jobs: Iterable[Job]) -> list[Job]:
    """Deduplicate normalized jobs while preserving source order."""

    unique: list[Job] = []
    seen: set[str] = set()
    for job in jobs:
        key = _job_key(job)
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def _job_key(job: Job) -> str:
    if job.apply_url:
        return str(job.apply_url).rstrip("/").casefold()
    if job.source_job_id:
        return f"{job.source}|{job.source_job_id}".casefold()
    return f"{job.title}|{job.company}|{job.location or ''}".casefold()
