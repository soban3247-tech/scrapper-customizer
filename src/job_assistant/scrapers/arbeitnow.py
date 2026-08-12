"""Arbeitnow public API adapter."""

from typing import Any

import requests
from pydantic import ValidationError

from job_assistant.models import Job, JobSource, SearchConfig

from .base import ScrapeResult, ScraperCapabilities, ScraperIssue
from .errors import ScraperResponseError
from .http import create_session, request_json
from .parsing import parse_job_date, string_list, text_matches_query


class ArbeitnowScraper:
    """Fetch paginated Arbeitnow jobs and apply the user's text query."""

    source_id = JobSource.ARBEITNOW.value
    display_name = "Arbeitnow"
    capabilities = ScraperCapabilities(
        supports_pagination=True,
        supports_location=True,
    )
    api_url = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or create_session()

    def search(self, config: SearchConfig) -> ScrapeResult:
        jobs: list[Job] = []
        issues: list[ScraperIssue] = []

        for page in range(1, config.max_pages + 1):
            payload = request_json(self._session, self.api_url, params={"page": page})
            raw_jobs = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(raw_jobs, list):
                raise ScraperResponseError("Arbeitnow response did not contain a data list")
            if not raw_jobs:
                break

            for index, raw_job in enumerate(raw_jobs):
                if not isinstance(raw_job, dict):
                    issues.append(self._invalid_job_issue(page, index))
                    continue
                if not text_matches_query(
                    config.query,
                    raw_job.get("title"),
                    raw_job.get("company_name"),
                    raw_job.get("description"),
                    raw_job.get("tags"),
                ):
                    continue
                try:
                    jobs.append(self._normalize(raw_job))
                except (TypeError, ValueError, ValidationError):
                    issues.append(self._invalid_job_issue(page, index))

            links = payload.get("links") if isinstance(payload, dict) else None
            if not isinstance(links, dict) or not links.get("next"):
                break

        return ScrapeResult(source_id=self.source_id, jobs=jobs, issues=issues)

    def _normalize(self, raw_job: dict[str, Any]) -> Job:
        job_types = string_list(raw_job.get("job_types"))
        return Job(
            source=self.display_name,
            source_job_id=_first_identifier(raw_job.get("slug"), raw_job.get("id")),
            title=raw_job.get("title"),
            company=raw_job.get("company_name"),
            description=raw_job.get("description") or "",
            location=raw_job.get("location"),
            workplace_type="Remote" if raw_job.get("remote") else None,
            commitment=", ".join(job_types) or None,
            posted_date=parse_job_date(raw_job.get("created_at")),
            apply_url=raw_job.get("url"),
            tags=string_list(raw_job.get("tags")),
        )

    def _invalid_job_issue(self, page: int, index: int) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code="invalid_job",
            message=f"Arbeitnow job at page {page}, index {index} could not be normalized",
        )


def _first_identifier(*values: Any) -> str | None:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return None

