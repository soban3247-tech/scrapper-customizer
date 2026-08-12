"""Remotive public API adapter."""

from typing import Any

import requests
from pydantic import ValidationError

from job_assistant.models import Job, JobSource, SearchConfig

from .base import ScrapeResult, ScraperCapabilities, ScraperIssue
from .errors import ScraperResponseError
from .http import create_session, request_json
from .parsing import parse_job_date, string_list


class RemotiveScraper:
    """Fetch and normalize vacancies from Remotive's public API."""

    source_id = JobSource.REMOTIVE.value
    display_name = "Remotive"
    capabilities = ScraperCapabilities(supports_location=True)
    api_url = "https://remotive.com/api/remote-jobs"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or create_session()

    def search(self, config: SearchConfig) -> ScrapeResult:
        payload = request_json(
            self._session,
            self.api_url,
            params={"search": config.query},
        )
        raw_jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(raw_jobs, list):
            raise ScraperResponseError("Remotive response did not contain a jobs list")

        jobs: list[Job] = []
        issues: list[ScraperIssue] = []
        for index, raw_job in enumerate(raw_jobs):
            if not isinstance(raw_job, dict):
                issues.append(self._invalid_job_issue(index))
                continue
            try:
                jobs.append(self._normalize(raw_job))
            except (TypeError, ValueError, ValidationError):
                issues.append(self._invalid_job_issue(index))
        return ScrapeResult(source_id=self.source_id, jobs=jobs, issues=issues)

    def _normalize(self, raw_job: dict[str, Any]) -> Job:
        return Job(
            source=self.display_name,
            source_job_id=_optional_string(raw_job.get("id")),
            title=raw_job.get("title"),
            company=raw_job.get("company_name"),
            description=raw_job.get("description") or "",
            location=raw_job.get("candidate_required_location"),
            workplace_type="Remote",
            commitment=raw_job.get("job_type"),
            posted_date=parse_job_date(raw_job.get("publication_date")),
            apply_url=raw_job.get("url"),
            tags=string_list(raw_job.get("tags")),
        )

    def _invalid_job_issue(self, index: int) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code="invalid_job",
            message=f"Remotive job at index {index} could not be normalized",
        )


def _optional_string(value: Any) -> str | None:
    return None if value in (None, "") else str(value)

