"""Lever public postings API adapter."""

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


class LeverScraper:
    """Fetch jobs from one or more configured Lever companies."""

    source_id = JobSource.LEVER.value
    display_name = "Lever"
    capabilities = ScraperCapabilities(
        supports_location=True,
        configuration_fields=(
            ScraperConfigField(
                key="companies",
                label="Lever company names",
                kind=ConfigFieldKind.STRING_LIST,
                required=True,
                help_text="For example: netflix",
            ),
        ),
    )
    api_url = "https://api.lever.co/v0/postings/{company}"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or create_session()

    def search(self, config: SearchConfig) -> ScrapeResult:
        companies = configured_targets(
            config,
            source_id=self.source_id,
            option_key="companies",
            legacy_values=config.lever_companies,
            target_label="Lever company name",
        )
        jobs: list[Job] = []
        issues: list[ScraperIssue] = []
        successful_companies = 0
        last_error: ScraperError | None = None

        for company in companies:
            try:
                payload = request_json(
                    self._session,
                    self.api_url.format(company=quote(company, safe="")),
                    params={"mode": "json"},
                )
                if not isinstance(payload, list):
                    raise ScraperResponseError(
                        f"Lever company {company} did not return a jobs list"
                    )
                successful_companies += 1
            except ScraperError as exc:
                last_error = exc
                issues.append(self._target_issue(company, exc))
                continue

            for index, raw_job in enumerate(payload):
                if not isinstance(raw_job, dict):
                    issues.append(self._invalid_job_issue(company, index))
                    continue
                categories = raw_job.get("categories") or {}
                lists = raw_job.get("lists") or []
                if not text_matches_query(
                    config.query,
                    raw_job.get("text"),
                    raw_job.get("descriptionPlain"),
                    categories,
                    lists,
                ):
                    continue
                try:
                    jobs.append(self._normalize(raw_job, company))
                except (TypeError, ValueError, ValidationError):
                    issues.append(self._invalid_job_issue(company, index))

        if successful_companies == 0 and last_error is not None:
            raise last_error
        return ScrapeResult(source_id=self.source_id, jobs=jobs, issues=issues)

    def _normalize(self, raw_job: dict[str, Any], company: str) -> Job:
        categories = raw_job.get("categories")
        if not isinstance(categories, dict):
            categories = {}
        return Job(
            source=self.display_name,
            source_job_id=_optional_string(raw_job.get("id")),
            title=raw_job.get("text"),
            company=company,
            description=raw_job.get("descriptionPlain") or "",
            location=categories.get("location"),
            commitment=categories.get("commitment"),
            posted_date=parse_job_date(raw_job.get("createdAt")),
            apply_url=raw_job.get("hostedUrl") or raw_job.get("applyUrl"),
        )

    def _target_issue(self, company: str, error: ScraperError) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code=error.code,
            message=f"Lever company {company} failed: {error}",
            retryable=error.retryable,
        )

    def _invalid_job_issue(self, company: str, index: int) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code="invalid_job",
            message=(
                f"Lever job at company {company}, index {index} "
                "could not be normalized"
            ),
        )


def _optional_string(value: Any) -> str | None:
    return None if value in (None, "") else str(value)
