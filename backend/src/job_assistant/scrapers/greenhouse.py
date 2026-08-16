"""Greenhouse public job-board API adapter."""

from typing import Any
from urllib.parse import quote

import requests
from pydantic import ValidationError

from job_assistant.models import Job, JobSource, SearchConfig

from .base import (
    ConfigFieldKind,
    ScrapeResult,
    ScraperCapabilities,
    ScraperConfigField,
    ScraperIssue,
)
from .configuration import configured_targets
from .errors import ScraperError, ScraperResponseError
from .http import create_session, request_json
from .parsing import parse_job_date, text_matches_query


class GreenhouseScraper:
    """Fetch jobs from one or more configured Greenhouse boards."""

    source_id = JobSource.GREENHOUSE.value
    display_name = "Greenhouse"
    capabilities = ScraperCapabilities(
        supports_location=True,
        configuration_fields=(
            ScraperConfigField(
                key="boards",
                label="Greenhouse board names",
                kind=ConfigFieldKind.STRING_LIST,
                required=True,
                help_text="For example: openai",
            ),
        ),
    )
    api_url = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or create_session()

    def search(self, config: SearchConfig) -> ScrapeResult:
        boards = configured_targets(
            config,
            source_id=self.source_id,
            option_key="boards",
            legacy_values=config.greenhouse_boards,
            target_label="Greenhouse board name",
        )
        jobs: list[Job] = []
        issues: list[ScraperIssue] = []
        successful_boards = 0
        last_error: ScraperError | None = None

        for board in boards:
            try:
                payload = request_json(
                    self._session,
                    self.api_url.format(board=quote(board, safe="")),
                    params={"content": "true"},
                )
                raw_jobs = payload.get("jobs") if isinstance(payload, dict) else None
                if not isinstance(raw_jobs, list):
                    raise ScraperResponseError(
                        f"Greenhouse board {board} did not return a jobs list"
                    )
                successful_boards += 1
            except ScraperError as exc:
                last_error = exc
                issues.append(self._target_issue(board, exc))
                continue

            for index, raw_job in enumerate(raw_jobs):
                if not isinstance(raw_job, dict):
                    issues.append(self._invalid_job_issue(board, index))
                    continue
                if not text_matches_query(
                    config.query,
                    raw_job.get("title"),
                    raw_job.get("content"),
                    raw_job.get("departments"),
                    raw_job.get("location"),
                ):
                    continue
                try:
                    jobs.append(self._normalize(raw_job, board))
                except (TypeError, ValueError, ValidationError):
                    issues.append(self._invalid_job_issue(board, index))

        if successful_boards == 0 and last_error is not None:
            raise last_error
        return ScrapeResult(source_id=self.source_id, jobs=jobs, issues=issues)

    def _normalize(self, raw_job: dict[str, Any], board: str) -> Job:
        location = raw_job.get("location")
        if isinstance(location, dict):
            location = location.get("name")
        return Job(
            source=self.display_name,
            source_job_id=_optional_string(raw_job.get("id")),
            title=raw_job.get("title"),
            company=board,
            description=raw_job.get("content") or "",
            location=location,
            posted_date=parse_job_date(raw_job.get("updated_at")),
            apply_url=raw_job.get("absolute_url"),
        )

    def _target_issue(self, board: str, error: ScraperError) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code=error.code,
            message=f"Greenhouse board {board} failed: {error}",
            retryable=error.retryable,
        )

    def _invalid_job_issue(self, board: str, index: int) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code="invalid_job",
            message=(
                f"Greenhouse job at board {board}, index {index} "
                "could not be normalized"
            ),
        )


def _optional_string(value: Any) -> str | None:
    return None if value in (None, "") else str(value)
