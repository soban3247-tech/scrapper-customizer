"""Ashby public job-board API adapter."""

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
from .parsing import optional_decimal, parse_job_date, text_matches_query


class AshbyScraper:
    """Fetch jobs from one or more configured Ashby organizations."""

    source_id = JobSource.ASHBY.value
    display_name = "Ashby"
    capabilities = ScraperCapabilities(
        supports_location=True,
        configuration_fields=(
            ScraperConfigField(
                key="organizations",
                label="Ashby organization names",
                kind=ConfigFieldKind.STRING_LIST,
                required=True,
                help_text="For example: openai",
            ),
        ),
    )
    api_url = "https://api.ashbyhq.com/posting-api/job-board/{organization}"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or create_session()

    def search(self, config: SearchConfig) -> ScrapeResult:
        organizations = configured_targets(
            config,
            source_id=self.source_id,
            option_key="organizations",
            legacy_values=config.ashby_organizations,
            target_label="Ashby organization name",
        )
        jobs: list[Job] = []
        issues: list[ScraperIssue] = []
        successful_organizations = 0
        last_error: ScraperError | None = None

        for organization in organizations:
            try:
                payload = request_json(
                    self._session,
                    self.api_url.format(organization=quote(organization, safe="")),
                    params={"includeCompensation": "true"},
                )
                raw_jobs = payload.get("jobs") if isinstance(payload, dict) else None
                if not isinstance(raw_jobs, list):
                    raise ScraperResponseError(
                        f"Ashby organization {organization} did not return a jobs list"
                    )
                successful_organizations += 1
            except ScraperError as exc:
                last_error = exc
                issues.append(self._target_issue(organization, exc))
                continue

            for index, raw_job in enumerate(raw_jobs):
                if not isinstance(raw_job, dict):
                    issues.append(self._invalid_job_issue(organization, index))
                    continue
                if not text_matches_query(
                    config.query,
                    raw_job.get("title"),
                    raw_job.get("descriptionPlain"),
                    raw_job.get("department"),
                    raw_job.get("location"),
                ):
                    continue
                try:
                    jobs.append(self._normalize(raw_job, organization))
                except (TypeError, ValueError, ValidationError):
                    issues.append(self._invalid_job_issue(organization, index))

        if successful_organizations == 0 and last_error is not None:
            raise last_error
        return ScrapeResult(source_id=self.source_id, jobs=jobs, issues=issues)

    def _normalize(self, raw_job: dict[str, Any], organization: str) -> Job:
        compensation = raw_job.get("compensation")
        if not isinstance(compensation, dict):
            compensation = {}
        return Job(
            source=self.display_name,
            source_job_id=_optional_string(raw_job.get("id")),
            title=raw_job.get("title"),
            company=organization,
            description=raw_job.get("descriptionPlain") or "",
            location=_name_or_string(raw_job.get("location")),
            commitment=_name_or_string(raw_job.get("department")),
            posted_date=parse_job_date(
                raw_job.get("publishedAt")
                or raw_job.get("createdAt")
                or raw_job.get("updatedAt")
            ),
            apply_url=raw_job.get("jobUrl") or raw_job.get("applyUrl"),
            salary_min=optional_decimal(compensation.get("minValue")),
            salary_max=optional_decimal(compensation.get("maxValue")),
            salary_currency=_currency_code(compensation),
        )

    def _target_issue(self, organization: str, error: ScraperError) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code=error.code,
            message=f"Ashby organization {organization} failed: {error}",
            retryable=error.retryable,
        )

    def _invalid_job_issue(self, organization: str, index: int) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code="invalid_job",
            message=(
                f"Ashby job at organization {organization}, index {index} "
                "could not be normalized"
            ),
        )


def _name_or_string(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("name")
    return None if value in (None, "") else str(value)


def _optional_string(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _currency_code(compensation: dict[str, Any]) -> str | None:
    value = compensation.get("currencyCode") or compensation.get("currency")
    if not isinstance(value, str) or len(value.strip()) != 3:
        return None
    return value.strip().upper()
