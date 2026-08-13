"""HiringCafe Next.js data adapter."""

import json
import random
import re
import time
from collections.abc import Callable
from typing import Any

import requests
from pydantic import ValidationError

from job_assistant.models import Job, JobSource, SearchConfig

from .base import ScrapeResult, ScraperCapabilities, ScraperIssue
from .errors import ScraperRequestError, ScraperResponseError
from .http import create_session
from .parsing import optional_decimal, parse_job_date, string_list

NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


class HiringCafeScraper:
    """Discover HiringCafe's active build and normalize its paginated results."""

    source_id = JobSource.HIRINGCAFE.value
    display_name = "HiringCafe"
    capabilities = ScraperCapabilities(
        supports_pagination=True,
        supports_posted_after=True,
        supports_location=True,
    )
    base_url = "https://hiringcafe.com"

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._session = session or create_session()
        self._sleep = sleep

    def search(self, config: SearchConfig) -> ScrapeResult:
        build_id = self._get_build_id()
        search_state = self._build_search_state(config.query)
        jobs: list[Job] = []
        issues: list[ScraperIssue] = []
        seen: set[str] = set()

        for page in range(config.max_pages):
            page_props, build_id = self._fetch_page(
                build_id,
                search_state,
                page,
            )
            raw_jobs = page_props.get("ssrHits")
            if raw_jobs is None:
                raw_jobs = page_props.get("results")
            if not isinstance(raw_jobs, list):
                raise ScraperResponseError(
                    "HiringCafe response did not contain a recognized jobs list"
                )
            if not raw_jobs:
                break

            for index, raw_job in enumerate(raw_jobs):
                if not isinstance(raw_job, dict):
                    issues.append(self._invalid_job_issue(page, index))
                    continue
                identity = self._identity(raw_job)
                if identity in seen:
                    continue
                seen.add(identity)
                try:
                    jobs.append(self._normalize(raw_job))
                except (TypeError, ValueError, ValidationError):
                    issues.append(self._invalid_job_issue(page, index))

            if page_props.get("ssrIsLastPage") is True:
                break
            self._sleep(random.uniform(1.0, 1.8))

        return ScrapeResult(source_id=self.source_id, jobs=jobs, issues=issues)

    def _get_build_id(self) -> str:
        response = self._get(
            self.base_url,
            headers={"Accept": "text/html,application/xhtml+xml"},
        )
        if response.status_code != 200:
            raise ScraperRequestError(
                f"HiringCafe homepage returned HTTP {response.status_code}",
                retryable=response.status_code >= 500,
            )

        match = NEXT_DATA_RE.search(response.text)
        if match:
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                payload = {}
            if payload.get("buildId"):
                return str(payload["buildId"])

        fallback = re.search(r'"buildId"\s*:\s*"([^"]+)"', response.text)
        if fallback:
            return fallback.group(1)
        raise ScraperResponseError("HiringCafe build ID could not be discovered")

    def _fetch_page(
        self,
        build_id: str,
        search_state: dict[str, Any],
        page: int,
    ) -> tuple[dict[str, Any], str]:
        response = self._get_page(build_id, search_state, page)
        if response.status_code in {404, 410}:
            build_id = self._get_build_id()
            response = self._get_page(build_id, search_state, page)
        payload = self._parse_page_response(response, page + 1)
        page_props = payload.get("pageProps")
        if not isinstance(page_props, dict):
            raise ScraperResponseError("HiringCafe response did not contain pageProps")
        return page_props, build_id

    def _get_page(
        self,
        build_id: str,
        search_state: dict[str, Any],
        page: int,
    ) -> requests.Response:
        return self._get(
            f"{self.base_url}/_next/data/{build_id}/index.json",
            params={
                "searchState": json.dumps(search_state, separators=(",", ":")),
                "page": page,
            },
            headers={
                "Accept": "application/json,text/plain,*/*",
                "Referer": f"{self.base_url}/",
                "x-nextjs-data": "1",
            },
        )

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        last_error: requests.RequestException | None = None
        for attempt in range(4):
            try:
                response = self._session.get(
                    url,
                    timeout=30,
                    allow_redirects=True,
                    **kwargs,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 3:
                    self._sleep(2**attempt)
                    continue
                break
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                self._sleep(2**attempt)
                continue
            return response
        raise ScraperRequestError("HiringCafe request failed after retries") from last_error

    def _parse_page_response(
        self,
        response: requests.Response,
        page_number: int,
    ) -> dict[str, Any]:
        if response.status_code != 200:
            raise ScraperRequestError(
                f"HiringCafe returned HTTP {response.status_code} on page {page_number}",
                retryable=response.status_code >= 500 or response.status_code == 429,
            )
        content_type = response.headers.get("Content-Type", "").casefold()
        if "json" not in content_type:
            raise ScraperResponseError(
                f"HiringCafe returned non-JSON content on page {page_number}"
            )
        try:
            payload = response.json()
        except (requests.exceptions.JSONDecodeError, ValueError) as exc:
            raise ScraperResponseError(
                f"HiringCafe returned invalid JSON on page {page_number}"
            ) from exc
        if not isinstance(payload, dict):
            raise ScraperResponseError("HiringCafe returned an unexpected JSON structure")
        return payload

    @staticmethod
    def _build_search_state(query: str) -> dict[str, Any]:
        return {
            "locations": [
                {
                    "id": "FxY1yZQBoEtHp_8UEq7V",
                    "types": ["country"],
                    "formatted_address": "United States",
                    "address_components": [
                        {
                            "long_name": "United States",
                            "short_name": "US",
                            "types": ["country"],
                        }
                    ],
                    "workplace_types": ["Remote"],
                    "options": {
                        "flexible_regions": [
                            "anywhere_in_country",
                            "anywhere_in_continent",
                            "anywhere_in_world",
                        ]
                    },
                }
            ],
            "workplaceTypes": ["Remote"],
            "defaultToUserLocation": False,
            "userLocation": None,
            "searchQuery": query.strip(),
            "sortBy": "default",
        }

    def _normalize(self, raw_job: dict[str, Any]) -> Job:
        info = _dict(raw_job.get("job_information"))
        job_data = _dict(
            raw_job.get("v5_processed_job_data")
            or raw_job.get("processed_job_data")
            or raw_job.get("job_data")
        )
        company_data = _dict(
            raw_job.get("v5_processed_company_data")
            or raw_job.get("processed_company_data")
        )
        commitment = _first(job_data.get("commitment"), info.get("commitment"))
        if isinstance(commitment, list):
            commitment = ", ".join(str(item) for item in commitment)
        return Job(
            source=self.display_name,
            source_job_id=_optional_string(
                _first(raw_job.get("objectID"), raw_job.get("id"))
            ),
            title=_first(info.get("title"), job_data.get("title"), raw_job.get("title")),
            company=_first(
                job_data.get("company_name"),
                company_data.get("name"),
                info.get("company"),
                raw_job.get("company_name"),
                raw_job.get("company"),
                raw_job.get("board_token"),
            ),
            description=_first(
                job_data.get("description"),
                info.get("description"),
                raw_job.get("description"),
            )
            or "",
            location=_optional_string(
                _first(
                    job_data.get("formatted_workplace_location"),
                    info.get("location"),
                    raw_job.get("location"),
                )
            ),
            workplace_type=_optional_string(
                _first(
                    job_data.get("workplace_type"),
                    info.get("workplace_type"),
                    raw_job.get("workplace_type"),
                )
            ),
            commitment=_optional_string(commitment),
            posted_date=_posted_date(raw_job, info, job_data),
            apply_url=_first(
                raw_job.get("apply_url"),
                raw_job.get("url"),
                info.get("apply_url"),
            ),
            salary_min=optional_decimal(
                _first(job_data.get("yearly_min_compensation"), raw_job.get("salary_min"))
            ),
            salary_max=optional_decimal(
                _first(job_data.get("yearly_max_compensation"), raw_job.get("salary_max"))
            ),
            tags=string_list(raw_job.get("tags")),
        )

    @staticmethod
    def _identity(raw_job: dict[str, Any]) -> str:
        return str(
            _first(
                raw_job.get("objectID"),
                raw_job.get("id"),
                raw_job.get("apply_url"),
                raw_job.get("url"),
                json.dumps(raw_job, sort_keys=True, default=str),
            )
        ).casefold()

    def _invalid_job_issue(self, page: int, index: int) -> ScraperIssue:
        return ScraperIssue(
            source_id=self.source_id,
            code="invalid_job",
            message=(
                f"HiringCafe job at page {page + 1}, index {index} "
                "could not be normalized"
            ),
        )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _optional_string(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _posted_date(
    raw_job: dict[str, Any],
    info: dict[str, Any],
    job_data: dict[str, Any],
) -> Any:
    for value in (
        job_data.get("date_posted"),
        job_data.get("posted_date"),
        job_data.get("published_at"),
        job_data.get("created_at"),
        job_data.get("estimated_publish_date"),
        info.get("date_posted"),
        info.get("posted_date"),
        info.get("published_at"),
        raw_job.get("date_posted"),
        raw_job.get("posted_date"),
        raw_job.get("published_at"),
        raw_job.get("created_at"),
        raw_job.get("createdAt"),
        raw_job.get("publication_date"),
        raw_job.get("first_seen_at"),
    ):
        parsed = parse_job_date(value)
        if parsed is not None:
            return parsed
    return None
