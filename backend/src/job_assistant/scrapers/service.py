"""Cross-source collection, deduplication, and date filtering."""

import re
from collections.abc import Iterable
from datetime import date

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


def filter_jobs_by_preferences(
    jobs: Iterable[Job],
    *,
    location: str | None,
    remote_only: bool,
) -> list[Job]:
    """Apply the shared location and remote-only search contract.

    Location matching requires a contiguous, case-insensitive token phrase in
    the job location. Remote-only searches retain jobs whose location or
    workplace type explicitly identifies them as remote. Jobs with missing or
    ambiguous values are excluded when the related filter is requested.
    """
    requested_location = _tokenize_location(location)
    filtered: list[Job] = []

    for job in jobs:
        job_location = _normalize_filter_text(job.location)
        workplace_type = _normalize_filter_text(job.workplace_type)

        if requested_location and not _contains_token_phrase(
            _tokenize_location(job.location), requested_location
        ):
            continue
        if remote_only and "remote" not in f"{job_location} {workplace_type}":
            continue
        filtered.append(job)

    return filtered


def _normalize_filter_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _tokenize_location(value: str | None) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+", (value or "").casefold()))


def _contains_token_phrase(
    location_tokens: tuple[str, ...], requested_tokens: tuple[str, ...]
) -> bool:
    phrase_length = len(requested_tokens)
    return any(
        location_tokens[index : index + phrase_length] == requested_tokens
        for index in range(len(location_tokens) - phrase_length + 1)
    )


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
