"""Remote OK public API adapter."""

from typing import Any

import requests
from pydantic import ValidationError

from job_assistant.models import Job, JobSource, SearchConfig

from .base import ScrapeResult, ScraperCapabilities, ScraperIssue
from .errors import ScraperError, ScraperRequestError, ScraperResponseError
from .http import create_session, request_json
from .parsing import (
    optional_decimal,
    parse_job_date,
    string_list,
    text_matches_query,
)


class RemoteOkScraper:
    """Fetch and normalize vacancies from Remote OK's public API."""

    source_id = JobSource.REMOTE_OK.value
    display_name = "Remote OK"
    capabilities = ScraperCapabilities(supports_location=True)
    api_urls = ("https://remoteok.com/api", "https://www.remoteok.com/api")

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or create_session()

    def search(self, config: SearchConfig) -> ScrapeResult:
        payload = self._fetch_with_fallback()
        if not isinstance(payload, list):
            raise ScraperResponseError("Remote OK response was not a list")

        jobs: list[Job] = []
        issues: list[ScraperIssue] = []
        for index, raw_job in enumerate(payload):
            if not isinstance(raw_job, dict) or "legal" in raw_job:
                continue
            if not text_matches_query(
                config.query,
                raw_job.get("position"),
                raw_job.get("company"),
                raw_job.get("description"),
                raw_job.get("tags"),
            ):
                continue
            try:
                jobs.append(self._normalize(raw_job))
            except (TypeError, ValueError, ValidationError):
                issues.append(self._invalid_job_issue(index))
        return ScrapeResult(source_id=self.source_id, jobs=jobs, issues=issues)

    def _fetch_with_fallback(self) -> Any:
        last_error: ScraperError | None = None
        for url in self.api_urls:
            try:
                return request_json(self._session, url)
            except ScraperError as exc:
                last_error = exc
        raise ScraperRequestError("Remote OK could not be reached") from last_error

    def _normalize(self, raw_job: dict[str, Any]) -> Job:
        return Job(
            source=self.display_name,
            source_job_id=_first_identifier(raw_job.get("id"), raw_job.get("slug")),
            title=raw_job.get("position"),
            company=raw_job.get("company"),
            description=raw_job.get("description") or "",
            location=raw_job.get("location"),
            workplace_type="Remote",
            posted_date=parse_job_date(raw_job.get("date")),
            apply_url=raw_job.get("url"),
            salary_min=optional_decimal(raw_job.get("salary_min")),
            salary_max=optional_decimal(raw_job.get("salary_max")),
            tags=string_list(raw_job.get("tags")),
        )

    def _invalid_job_issue(self, index: int) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code="invalid_job",
            message=f"Remote OK job at index {index} could not be normalized",
        )


def _first_identifier(*values: Any) -> str | None:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return None

