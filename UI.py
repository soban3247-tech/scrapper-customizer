from __future__ import annotations

import json
import queue
import random
import re
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import date, datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import pandas as pd
import requests


BASE_URL = "https://hiringcafe.com"

OTHER_JOB_PLATFORM_WEBPAGES = {
    "Remotive": "https://remotive.com/remote-jobs",
    "Arbeitnow": "https://www.arbeitnow.com/jobs",
    "Greenhouse job boards": "https://boards.greenhouse.io",
    "Lever job boards": "https://jobs.lever.co",
    "Ashby job boards": "https://jobs.ashbyhq.com",
    "Workable jobs": "https://jobs.workable.com",
    "Wellfound": "https://wellfound.com/jobs",
    "Remote OK": "https://remoteok.com",
}

SOURCE_LABELS = {
    "hiringcafe": "HiringCafe",
    "remotive": "Remotive",
    "arbeitnow": "Arbeitnow",
    "remoteok": "Remote OK",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "ashby": "Ashby",
}

NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

LogFn = Callable[[str], None]


class ScraperError(Exception):
    pass


def parse_user_date(value: str) -> date:
    """Parse a YYYY-MM-DD date entered by the user."""
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            "Date must use YYYY-MM-DD format, for example 2026-07-01."
        ) from exc

    today = datetime.now().date()
    if parsed > today:
        raise ValueError("Start date cannot be later than today.")
    return parsed


def parse_job_date(value: Any) -> date | None:
    """Convert common HiringCafe date formats to a date."""
    if value in (None, "", [], {}):
        return None

    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
        except (ValueError, OSError, OverflowError):
            return None

    text = str(value).strip()
    if not text:
        return None

    if text.isdigit():
        return parse_job_date(int(text))

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def get_job_posted_date(job: dict[str, Any]) -> date | None:
    """Find the posted/published date across known HiringCafe schemas."""
    info = job.get("job_information") or {}
    job_data = (
        job.get("v5_processed_job_data")
        or job.get("processed_job_data")
        or job.get("job_data")
        or {}
    )

    candidates = (
        job_data.get("date_posted"),
        job_data.get("posted_date"),
        job_data.get("published_at"),
        job_data.get("created_at"),
        job_data.get("estimated_publish_date"),
        info.get("date_posted"),
        info.get("posted_date"),
        info.get("published_at"),
        job.get("date_posted"),
        job.get("posted_date"),
        job.get("published_at"),
        job.get("created_at"),
        job.get("createdAt"),
        job.get("publication_date"),
        job.get("publicationDate"),
        job.get("first_seen_at"),
        job.get("firstSeenAt"),
    )

    for candidate in candidates:
        parsed = parse_job_date(candidate)
        if parsed is not None:
            return parsed
    return None


def filter_jobs_by_date(
    jobs: list[dict[str, Any]],
    start_date: date,
) -> tuple[list[dict[str, Any]], int]:
    """Keep jobs posted from start_date through today, inclusive."""
    today = datetime.now().date()
    filtered: list[dict[str, Any]] = []
    missing_date_count = 0

    for job in jobs:
        posted_date = get_job_posted_date(job)
        if posted_date is None:
            missing_date_count += 1
            continue
        if start_date <= posted_date <= today:
            job["_parsed_posted_date"] = posted_date.isoformat()
            filtered.append(job)

    return filtered, missing_date_count


def create_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )

    return session


def get_response(
    session: requests.Session,
    url: str,
    *,
    accept: str,
    retries: int = 4,
    log: LogFn | None = None,
) -> requests.Response:
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            response = session.get(
                url,
                headers={
                    "Accept": accept,
                    "Referer": f"{BASE_URL}/",
                },
                timeout=30,
                allow_redirects=True,
            )

            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt < retries - 1:
                    delay = (2**attempt) + random.uniform(0.5, 1.5)
                    if log:
                        log(
                            f"HTTP {response.status_code}. "
                            f"Retrying in {delay:.1f} seconds..."
                        )
                    time.sleep(delay)
                    continue

            return response

        except requests.RequestException as exc:
            last_error = exc

            if attempt < retries - 1:
                delay = (2**attempt) + random.uniform(0.5, 1.5)
                if log:
                    log(f"Connection failed. Retrying in {delay:.1f} seconds...")
                time.sleep(delay)

    raise ScraperError(f"Request failed after {retries} attempts: {last_error}")


def get_build_id(session: requests.Session, log: LogFn | None = None) -> str:
    response = get_response(
        session,
        BASE_URL,
        accept="text/html,application/xhtml+xml",
        log=log,
    )

    if response.status_code != 200:
        raise ScraperError(
            f"Could not open HiringCafe homepage. HTTP status: {response.status_code}"
        )

    match = NEXT_DATA_RE.search(response.text)

    if match:
        try:
            next_data = json.loads(match.group(1))
            build_id = next_data.get("buildId")

            if build_id:
                return str(build_id)

        except json.JSONDecodeError:
            pass

    build_match = re.search(
        r'"buildId"\s*:\s*"([^"]+)"',
        response.text,
    )

    if build_match:
        return build_match.group(1)

    page_preview = response.text[:500].replace("\n", " ")

    raise ScraperError(
        "Could not find HiringCafe's Next.js build ID.\n"
        "The homepage may be returning a bot-protection page.\n\n"
        f"Response preview:\n{page_preview}"
    )


def build_search_state(query: str) -> dict[str, Any]:
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


def parse_json_response(
    response: requests.Response,
    page_number: int,
) -> dict[str, Any]:
    content_type = response.headers.get("Content-Type", "").lower()
    body = response.text.strip()

    if response.status_code != 200:
        preview = body[:500].replace("\n", " ")

        raise ScraperError(
            f"HiringCafe returned HTTP {response.status_code} on page {page_number}.\n"
            f"Final URL: {response.url}\n"
            f"Response preview: {preview}"
        )

    if not body:
        raise ScraperError(f"HiringCafe returned an empty response on page {page_number}.")

    if "json" not in content_type:
        preview = body[:500].replace("\n", " ")

        raise ScraperError(
            "HiringCafe returned HTML instead of JSON.\n"
            f"Page: {page_number}\n"
            f"Final URL: {response.url}\n"
            f"Content-Type: {content_type or 'missing'}\n\n"
            f"Response preview:\n{preview}"
        )

    try:
        payload = response.json()

    except requests.exceptions.JSONDecodeError as exc:
        preview = body[:500].replace("\n", " ")

        raise ScraperError(
            "HiringCafe returned invalid JSON.\n"
            f"Page: {page_number}\n"
            f"Final URL: {response.url}\n"
            f"Content-Type: {content_type}\n\n"
            f"Response preview:\n{preview}"
        ) from exc

    if not isinstance(payload, dict):
        raise ScraperError("HiringCafe returned an unexpected JSON structure.")

    return payload


def fetch_page(
    session: requests.Session,
    build_id: str,
    search_state: dict[str, Any],
    page: int,
    log: LogFn | None = None,
) -> tuple[dict[str, Any], str]:
    url = f"{BASE_URL}/_next/data/{build_id}/index.json"

    response = session.get(
        url,
        params={
            "searchState": json.dumps(search_state, separators=(",", ":")),
            "page": page,
        },
        headers={
            "Accept": "application/json,text/plain,*/*",
            "Referer": f"{BASE_URL}/",
            "x-nextjs-data": "1",
        },
        timeout=30,
        allow_redirects=True,
    )

    if response.status_code in {404, 410}:
        if log:
            log("Build ID expired. Getting the latest build ID...")

        build_id = get_build_id(session, log=log)
        url = f"{BASE_URL}/_next/data/{build_id}/index.json"

        response = session.get(
            url,
            params={
                "searchState": json.dumps(search_state, separators=(",", ":")),
                "page": page,
            },
            headers={
                "Accept": "application/json,text/plain,*/*",
                "Referer": f"{BASE_URL}/",
                "x-nextjs-data": "1",
            },
            timeout=30,
            allow_redirects=True,
        )

    payload = parse_json_response(response, page_number=page + 1)

    page_props = payload.get("pageProps")

    if not isinstance(page_props, dict):
        raise ScraperError(
            "The JSON response did not contain pageProps.\n"
            f"Available keys: {list(payload.keys())}"
        )

    return page_props, build_id


def scrape_jobs(
    query: str,
    max_pages: int = 5,
    log: LogFn | None = None,
) -> list[dict[str, Any]]:
    session = create_session()

    if log:
        log("Opening HiringCafe...")
    build_id = get_build_id(session, log=log)

    if log:
        log(f"Build ID: {build_id}")

    search_state = build_search_state(query)

    all_jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for page in range(max_pages):
        if log:
            log(f"Fetching page {page + 1}...")

        page_props, build_id = fetch_page(
            session,
            build_id,
            search_state,
            page,
            log=log,
        )

        results = page_props.get("ssrHits")

        if results is None:
            results = page_props.get("results")

        if not isinstance(results, list):
            raise ScraperError(
                "No recognized jobs list was found.\n"
                f"Available pageProps keys: {list(page_props.keys())}"
            )

        if not results:
            if log:
                log("No more jobs found.")
            break

        added = 0

        for job in results:
            if not isinstance(job, dict):
                continue

            unique_id = str(
                job.get("objectID")
                or job.get("id")
                or job.get("apply_url")
                or json.dumps(job, sort_keys=True, default=str)
            )

            if unique_id in seen_ids:
                continue

            seen_ids.add(unique_id)
            all_jobs.append(job)
            added += 1

        if log:
            log(f"Page {page + 1}: {len(results)} received, {added} added.")

        is_last_page = page_props.get("ssrIsLastPage")

        if is_last_page is True:
            break

        time.sleep(random.uniform(1.0, 1.8))

    return all_jobs


def request_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    log: LogFn | None = None,
) -> Any:
    try:
        response = session.get(
            url,
            params=params,
            headers={
                "Accept": "application/json,text/plain,*/*",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            },
            timeout=30,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        details = str(exc)
        if "NameResolutionError" in details or "getaddrinfo failed" in details:
            raise ScraperError(
                "DNS lookup failed, so this computer could not find the API server.\n"
                f"URL: {url}\n\n"
                "This is a network/DNS issue, not a company-name issue. Try opening "
                "the source website in a browser, changing DNS to 1.1.1.1 or 8.8.8.8, "
                "turning off VPN/proxy temporarily, or running: ipconfig /flushdns"
            ) from exc
        raise ScraperError(f"Request failed for {url}: {exc}") from exc

    if response.status_code != 200:
        preview = response.text[:300].replace("\n", " ")
        raise ScraperError(
            f"HTTP {response.status_code} from {url}. Response preview: {preview}"
        )

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        preview = response.text[:300].replace("\n", " ")
        raise ScraperError(
            f"Invalid JSON from {url}. Response preview: {preview}"
        ) from exc


def text_matches_query(query: str, *values: Any) -> bool:
    words = [word for word in re.split(r"\s+", query.lower().strip()) if word]
    if not words:
        return True

    haystack = " ".join(
        json.dumps(value, default=str).lower()
        if isinstance(value, (dict, list))
        else str(value).lower()
        for value in values
        if value not in (None, "", [], {})
    )

    return all(word in haystack for word in words)


def split_board_names(value: str) -> list[str]:
    return [
        item.strip().strip("/")
        for item in re.split(r"[\n,;]+", value)
        if item.strip()
    ]


def mark_platform(job: dict[str, Any], platform: str) -> dict[str, Any]:
    job["_platform"] = platform
    return job


def scrape_remotive_jobs(
    query: str,
    log: LogFn | None = None,
) -> list[dict[str, Any]]:
    if log:
        log("Fetching Remotive jobs...")

    session = create_session()
    payload = request_json(
        session,
        "https://remotive.com/api/remote-jobs",
        params={"search": query},
        log=log,
    )

    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(jobs, list):
        raise ScraperError("Remotive response did not contain a jobs list.")

    results: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        results.append(
            mark_platform(
                {
                    "posted_date": job.get("publication_date"),
                    "title": job.get("title"),
                    "company_name": job.get("company_name"),
                    "location": job.get("candidate_required_location"),
                    "workplace_type": "Remote",
                    "commitment": job.get("job_type"),
                    "salary_min": "",
                    "salary_max": "",
                    "apply_url": job.get("url"),
                    "source": "Remotive",
                    "id": job.get("id"),
                    "description": job.get("description"),
                    "tags": job.get("tags"),
                },
                "Remotive",
            )
        )

    if log:
        log(f"Remotive returned {len(results)} jobs.")
    return results


def scrape_arbeitnow_jobs(
    query: str,
    max_pages: int,
    log: LogFn | None = None,
) -> list[dict[str, Any]]:
    if log:
        log("Fetching Arbeitnow jobs...")

    session = create_session()
    results: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        payload = request_json(
            session,
            "https://www.arbeitnow.com/api/job-board-api",
            params={"page": page},
            log=log,
        )
        jobs = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(jobs, list) or not jobs:
            break

        added = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            if not text_matches_query(
                query,
                job.get("title"),
                job.get("company_name"),
                job.get("description"),
                job.get("tags"),
            ):
                continue

            results.append(
                mark_platform(
                    {
                        "posted_date": job.get("created_at"),
                        "title": job.get("title"),
                        "company_name": job.get("company_name"),
                        "location": job.get("location"),
                        "workplace_type": "Remote" if job.get("remote") else "",
                        "commitment": ", ".join(job.get("job_types") or []),
                        "apply_url": job.get("url"),
                        "source": "Arbeitnow",
                        "id": job.get("slug") or job.get("id"),
                        "description": job.get("description"),
                        "tags": job.get("tags"),
                    },
                    "Arbeitnow",
                )
            )
            added += 1

        if log:
            log(f"Arbeitnow page {page}: {len(jobs)} received, {added} matched.")

        links = payload.get("links") if isinstance(payload, dict) else {}
        if not isinstance(links, dict) or not links.get("next"):
            break

    if log:
        log(f"Arbeitnow matched {len(results)} jobs.")
    return results


def scrape_remoteok_jobs(
    query: str,
    log: LogFn | None = None,
) -> list[dict[str, Any]]:
    if log:
        log("Fetching Remote OK jobs...")

    session = create_session()
    last_error: Exception | None = None
    payload: Any = None

    for url in ("https://remoteok.com/api", "https://www.remoteok.com/api"):
        try:
            payload = request_json(session, url, log=log)
            break
        except (ScraperError, requests.RequestException) as exc:
            last_error = exc

    if payload is None:
        raise ScraperError(f"Remote OK could not be reached: {last_error}")

    if not isinstance(payload, list):
        raise ScraperError("Remote OK response was not a list.")

    results: list[dict[str, Any]] = []
    for job in payload:
        if not isinstance(job, dict) or "legal" in job:
            continue
        if not text_matches_query(
            query,
            job.get("position"),
            job.get("company"),
            job.get("description"),
            job.get("tags"),
        ):
            continue

        results.append(
            mark_platform(
                {
                    "posted_date": job.get("date"),
                    "title": job.get("position"),
                    "company_name": job.get("company"),
                    "location": job.get("location"),
                    "workplace_type": "Remote",
                    "commitment": "",
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "apply_url": job.get("url"),
                    "source": "Remote OK",
                    "id": job.get("id") or job.get("slug"),
                    "description": job.get("description"),
                    "tags": job.get("tags"),
                },
                "Remote OK",
            )
        )

    if log:
        log(f"Remote OK matched {len(results)} jobs.")
    return results


def scrape_greenhouse_jobs(
    query: str,
    board_names: list[str],
    log: LogFn | None = None,
) -> list[dict[str, Any]]:
    session = create_session()
    results: list[dict[str, Any]] = []

    for board in board_names:
        if log:
            log(f"Fetching Greenhouse board: {board}")

        payload = request_json(
            session,
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
            params={"content": "true"},
            log=log,
        )
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ScraperError(f"Greenhouse board {board} did not return jobs.")

        added = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            if not text_matches_query(
                query,
                job.get("title"),
                job.get("content"),
                job.get("departments"),
                job.get("location"),
            ):
                continue

            location = job.get("location") or {}
            results.append(
                mark_platform(
                    {
                        "posted_date": job.get("updated_at"),
                        "title": job.get("title"),
                        "company_name": board,
                        "location": location.get("name")
                        if isinstance(location, dict)
                        else location,
                        "workplace_type": "",
                        "commitment": "",
                        "apply_url": job.get("absolute_url"),
                        "source": "Greenhouse",
                        "id": job.get("id"),
                        "description": job.get("content"),
                    },
                    "Greenhouse",
                )
            )
            added += 1

        if log:
            log(f"Greenhouse {board}: {added} matched.")

    return results


def scrape_lever_jobs(
    query: str,
    company_names: list[str],
    log: LogFn | None = None,
) -> list[dict[str, Any]]:
    session = create_session()
    results: list[dict[str, Any]] = []

    for company in company_names:
        if log:
            log(f"Fetching Lever company: {company}")

        payload = request_json(
            session,
            f"https://api.lever.co/v0/postings/{company}",
            params={"mode": "json"},
            log=log,
        )
        if not isinstance(payload, list):
            raise ScraperError(f"Lever company {company} did not return a list.")

        added = 0
        for job in payload:
            if not isinstance(job, dict):
                continue
            categories = job.get("categories") or {}
            lists = job.get("lists") or []
            if not text_matches_query(
                query,
                job.get("text"),
                job.get("descriptionPlain"),
                categories,
                lists,
            ):
                continue

            results.append(
                mark_platform(
                    {
                        "posted_date": job.get("createdAt"),
                        "title": job.get("text"),
                        "company_name": company,
                        "location": categories.get("location")
                        if isinstance(categories, dict)
                        else "",
                        "workplace_type": "",
                        "commitment": categories.get("commitment")
                        if isinstance(categories, dict)
                        else "",
                        "apply_url": job.get("hostedUrl") or job.get("applyUrl"),
                        "source": "Lever",
                        "id": job.get("id"),
                        "description": job.get("descriptionPlain"),
                    },
                    "Lever",
                )
            )
            added += 1

        if log:
            log(f"Lever {company}: {added} matched.")

    return results


def scrape_ashby_jobs(
    query: str,
    organization_names: list[str],
    log: LogFn | None = None,
) -> list[dict[str, Any]]:
    session = create_session()
    results: list[dict[str, Any]] = []

    for organization in organization_names:
        if log:
            log(f"Fetching Ashby organization: {organization}")

        payload = request_json(
            session,
            f"https://api.ashbyhq.com/posting-api/job-board/{organization}",
            params={"includeCompensation": "true"},
            log=log,
        )
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ScraperError(f"Ashby organization {organization} did not return jobs.")

        added = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            if not text_matches_query(
                query,
                job.get("title"),
                job.get("descriptionPlain"),
                job.get("department"),
                job.get("location"),
            ):
                continue

            location = job.get("location") or {}
            department = job.get("department") or {}
            compensation = job.get("compensation") or {}
            results.append(
                mark_platform(
                    {
                        "posted_date": job.get("publishedAt")
                        or job.get("createdAt")
                        or job.get("updatedAt"),
                        "title": job.get("title"),
                        "company_name": organization,
                        "location": location.get("name")
                        if isinstance(location, dict)
                        else location,
                        "workplace_type": "",
                        "commitment": department.get("name")
                        if isinstance(department, dict)
                        else "",
                        "salary_min": compensation.get("minValue")
                        if isinstance(compensation, dict)
                        else "",
                        "salary_max": compensation.get("maxValue")
                        if isinstance(compensation, dict)
                        else "",
                        "apply_url": job.get("jobUrl") or job.get("applyUrl"),
                        "source": "Ashby",
                        "id": job.get("id"),
                        "description": job.get("descriptionPlain"),
                    },
                    "Ashby",
                )
            )
            added += 1

        if log:
            log(f"Ashby {organization}: {added} matched.")

    return results


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique_jobs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for job in jobs:
        key = str(
            first_value(
                job.get("apply_url"),
                job.get("url"),
                job.get("absolute_url"),
                job.get("id"),
                job.get("objectID"),
                f"{job.get('title')}|{job.get('company_name') or job.get('company')}",
            )
        ).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_jobs.append(job)

    return unique_jobs


def scrape_selected_sources(
    *,
    query: str,
    max_pages: int,
    selected_sources: dict[str, bool],
    greenhouse_boards: list[str],
    lever_companies: list[str],
    ashby_organizations: list[str],
    log: LogFn,
) -> list[dict[str, Any]]:
    all_jobs: list[dict[str, Any]] = []

    collectors: list[tuple[str, Callable[[], list[dict[str, Any]]]]] = []

    if selected_sources.get("hiringcafe"):
        collectors.append(
            ("HiringCafe", lambda: [mark_platform(job, "HiringCafe") for job in scrape_jobs(query, max_pages, log)])
        )
    if selected_sources.get("remotive"):
        collectors.append(("Remotive", lambda: scrape_remotive_jobs(query, log)))
    if selected_sources.get("arbeitnow"):
        collectors.append(("Arbeitnow", lambda: scrape_arbeitnow_jobs(query, max_pages, log)))
    if selected_sources.get("remoteok"):
        collectors.append(("Remote OK", lambda: scrape_remoteok_jobs(query, log)))
    if selected_sources.get("greenhouse") and greenhouse_boards:
        collectors.append(
            ("Greenhouse", lambda: scrape_greenhouse_jobs(query, greenhouse_boards, log))
        )
    if selected_sources.get("lever") and lever_companies:
        collectors.append(("Lever", lambda: scrape_lever_jobs(query, lever_companies, log)))
    if selected_sources.get("ashby") and ashby_organizations:
        collectors.append(
            ("Ashby", lambda: scrape_ashby_jobs(query, ashby_organizations, log))
        )

    for source_name, collector in collectors:
        try:
            jobs = collector()
            all_jobs.extend(jobs)
            log(f"{source_name}: added {len(jobs)} jobs before date filtering.")
        except ScraperError as exc:
            log(f"{source_name} failed: {exc}")
        except requests.RequestException as exc:
            details = str(exc)
            if "NameResolutionError" in details or "getaddrinfo failed" in details:
                log(
                    f"{source_name} failed: DNS lookup failed. Your computer could "
                    "not find that source's API server. Try changing DNS to 1.1.1.1 "
                    "or 8.8.8.8, turning off VPN/proxy temporarily, or running "
                    "ipconfig /flushdns."
                )
            else:
                log(f"{source_name} request failed: {exc}")

    return deduplicate_jobs(all_jobs)


def first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value

    return ""


def clean_jobs(
    jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []

    for job in jobs:
        info = job.get("job_information") or {}

        job_data = (
            job.get("v5_processed_job_data")
            or job.get("processed_job_data")
            or {}
        )

        company_data = (
            job.get("v5_processed_company_data")
            or job.get("processed_company_data")
            or {}
        )

        commitment = first_value(
            job_data.get("commitment"),
            info.get("commitment"),
        )

        if isinstance(commitment, list):
            commitment = ", ".join(str(item) for item in commitment)

        parsed_posted_date = get_job_posted_date(job)

        cleaned.append(
            {
                "platform": first_value(
                    job.get("_platform"),
                    job.get("platform"),
                    job.get("source"),
                ),
                "posted_date": first_value(
                    job.get("_parsed_posted_date"),
                    parsed_posted_date.isoformat() if parsed_posted_date else "",
                ),
                "title": first_value(
                    info.get("title"),
                    job_data.get("title"),
                    job.get("title"),
                ),
                "company": first_value(
                    job_data.get("company_name"),
                    company_data.get("name"),
                    info.get("company"),
                    job.get("company_name"),
                    job.get("company"),
                    job.get("board_token"),
                ),
                "location": first_value(
                    job_data.get("formatted_workplace_location"),
                    info.get("location"),
                    job.get("location"),
                ),
                "workplace_type": first_value(
                    job_data.get("workplace_type"),
                    info.get("workplace_type"),
                    job.get("workplace_type"),
                ),
                "commitment": first_value(commitment, job.get("commitment")),
                "salary_min": first_value(
                    job_data.get("yearly_min_compensation"),
                    job.get("salary_min"),
                ),
                "salary_max": first_value(
                    job_data.get("yearly_max_compensation"),
                    job.get("salary_max"),
                ),
                "seniority": first_value(
                    job_data.get("seniority_level"),
                    job.get("seniority_level"),
                ),
                "apply_url": first_value(
                    job.get("apply_url"),
                    job.get("url"),
                    info.get("apply_url"),
                ),
                "source": first_value(
                    job.get("source"),
                    job.get("apply_source"),
                ),
                "job_id": first_value(
                    job.get("objectID"),
                    job.get("id"),
                ),
            }
        )

    return cleaned


def make_filename(query: str) -> str:
    safe_query = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        query,
    ).strip("_")

    return f"{safe_query.lower()}_jobs.xlsx"


def export_to_excel(
    jobs: list[dict[str, Any]],
    filename: str | Path,
) -> Path:
    output = Path(filename)
    output.parent.mkdir(parents=True, exist_ok=True)

    dataframe = pd.DataFrame(jobs)

    dataframe.to_excel(
        output,
        index=False,
        engine="openpyxl",
    )

    return output.resolve()


def run_scraper_workflow(
    *,
    query: str,
    start_date: date,
    max_pages: int,
    output_filename: str | Path,
    selected_sources: dict[str, bool],
    greenhouse_boards: list[str],
    lever_companies: list[str],
    ashby_organizations: list[str],
    log: LogFn,
) -> Path | None:
    raw_jobs = scrape_selected_sources(
        query=query,
        max_pages=max_pages,
        selected_sources=selected_sources,
        greenhouse_boards=greenhouse_boards,
        lever_companies=lever_companies,
        ashby_organizations=ashby_organizations,
        log=log,
    )

    if not raw_jobs:
        log("No jobs found from the selected sources.")
        return None

    dated_jobs, missing_date_count = filter_jobs_by_date(
        raw_jobs,
        start_date,
    )

    log(
        f"Date filter: {start_date.isoformat()} to "
        f"{datetime.now().date().isoformat()}"
    )
    log(f"Jobs inside date range: {len(dated_jobs)}")

    if missing_date_count:
        log(
            f"Skipped {missing_date_count} jobs because the source did not "
            "provide a recognizable posted date."
        )

    if not dated_jobs:
        log("No jobs were found inside the selected date range.")
        return None

    cleaned_jobs = clean_jobs(dated_jobs)
    saved_path = export_to_excel(cleaned_jobs, output_filename)
    log(f"Saved: {saved_path}")
    log(f"Completed: {len(cleaned_jobs)} jobs saved.")

    return saved_path


class HiringCafeScraperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Job Scraper")
        self.root.geometry("820x640")
        self.root.minsize(720, 560)

        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.query_var = tk.StringVar()
        self.start_date_var = tk.StringVar(value=datetime.now().date().isoformat())
        self.max_pages_var = tk.StringVar(value="5")
        self.output_var = tk.StringVar(value=str(Path(make_filename("jobs")).resolve()))
        self.status_var = tk.StringVar(value="Ready")
        self.source_vars = {
            "hiringcafe": tk.BooleanVar(value=True),
            "remotive": tk.BooleanVar(value=True),
            "arbeitnow": tk.BooleanVar(value=True),
            "remoteok": tk.BooleanVar(value=True),
            "greenhouse": tk.BooleanVar(value=False),
            "lever": tk.BooleanVar(value=False),
            "ashby": tk.BooleanVar(value=False),
        }
        self.greenhouse_var = tk.StringVar()
        self.lever_var = tk.StringVar()
        self.ashby_var = tk.StringVar()

        self._build_ui()
        self.root.after(100, self._drain_log_queue)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        form = ttk.Frame(self.root, padding=16)
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Job title").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Entry(form, textvariable=self.query_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(form, text="Start date").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Entry(form, textvariable=self.start_date_var, width=18).grid(
            row=1, column=1, sticky="w", pady=(10, 0)
        )
        ttk.Label(form, text="YYYY-MM-DD").grid(
            row=1, column=1, sticky="w", padx=(150, 0), pady=(10, 0)
        )

        ttk.Label(form, text="Maximum pages").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Spinbox(
            form,
            from_=1,
            to=100,
            textvariable=self.max_pages_var,
            width=8,
        ).grid(row=2, column=1, sticky="w", pady=(10, 0))

        ttk.Label(form, text="Output file").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Entry(form, textvariable=self.output_var).grid(
            row=3, column=1, sticky="ew", pady=(10, 0)
        )
        ttk.Button(form, text="Browse", command=self._browse_output).grid(
            row=3, column=2, sticky="e", padx=(10, 0), pady=(10, 0)
        )

        platforms = ttk.LabelFrame(form, text="Sources to scrape")
        platforms.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        platforms.columnconfigure(3, weight=1)

        source_order = (
            "hiringcafe",
            "remotive",
            "arbeitnow",
            "remoteok",
            "greenhouse",
            "lever",
            "ashby",
        )

        for index, source_key in enumerate(source_order):
            ttk.Checkbutton(
                platforms,
                text=SOURCE_LABELS[source_key],
                variable=self.source_vars[source_key],
            ).grid(
                row=index // 4,
                column=index % 4,
                sticky="w",
                padx=8,
                pady=4,
            )

        ttk.Label(
            platforms,
            text="Greenhouse boards",
        ).grid(row=2, column=0, sticky="w", padx=8, pady=(10, 0))
        ttk.Entry(platforms, textvariable=self.greenhouse_var).grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=8, pady=(10, 0)
        )

        ttk.Label(
            platforms,
            text="Lever companies",
        ).grid(row=3, column=0, sticky="w", padx=8, pady=(8, 0))
        ttk.Entry(platforms, textvariable=self.lever_var).grid(
            row=3, column=1, columnspan=3, sticky="ew", padx=8, pady=(8, 0)
        )

        ttk.Label(
            platforms,
            text="Ashby orgs",
        ).grid(row=4, column=0, sticky="w", padx=8, pady=(8, 8))
        ttk.Entry(platforms, textvariable=self.ashby_var).grid(
            row=4, column=1, columnspan=3, sticky="ew", padx=8, pady=(8, 8)
        )

        links_text = "Source pages: " + " | ".join(
            f"{name}: {url}" for name, url in OTHER_JOB_PLATFORM_WEBPAGES.items()
        )
        ttk.Label(platforms, text=links_text, wraplength=760).grid(
            row=5, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 8)
        )

        button_row = ttk.Frame(form)
        button_row.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        button_row.columnconfigure(1, weight=1)

        self.start_button = ttk.Button(
            button_row,
            text="Start Scraping",
            command=self._start_scraping,
        )
        self.start_button.grid(row=0, column=0, sticky="w")

        ttk.Label(button_row, textvariable=self.status_var).grid(
            row=0, column=1, sticky="e"
        )

        log_frame = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=16,
            wrap="word",
            state="disabled",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log_text.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _open_platform_links(self) -> None:
        for url in OTHER_JOB_PLATFORM_WEBPAGES.values():
            webbrowser.open_new_tab(url)

    def _browse_output(self) -> None:
        initial = Path(self.output_var.get() or ".")
        filename = filedialog.asksaveasfilename(
            title="Choose Excel output file",
            initialdir=str(initial.parent if initial.parent.exists() else Path.cwd()),
            initialfile=initial.name if initial.name else "jobs.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx"), ("All files", "*.*")],
        )
        if filename:
            self.output_var.set(filename)

    def _validate_inputs(
        self,
    ) -> tuple[str, date, int, Path, dict[str, bool], list[str], list[str], list[str]] | None:
        query = self.query_var.get().strip()
        if not query:
            messagebox.showerror("Missing job title", "Please enter a job title.")
            return None

        try:
            start_date = parse_user_date(self.start_date_var.get())
        except ValueError as exc:
            messagebox.showerror("Invalid start date", str(exc))
            return None

        try:
            max_pages = int(self.max_pages_var.get())
        except ValueError:
            messagebox.showerror("Invalid pages", "Maximum pages must be a number.")
            return None

        if max_pages < 1:
            messagebox.showerror("Invalid pages", "Maximum pages must be at least 1.")
            return None

        output_text = self.output_var.get().strip()
        if not output_text:
            output_text = make_filename(query)

        output_path = Path(output_text)
        if output_path.suffix.lower() != ".xlsx":
            output_path = output_path.with_suffix(".xlsx")

        selected_sources = {
            source_key: source_var.get()
            for source_key, source_var in self.source_vars.items()
        }

        greenhouse_boards = split_board_names(self.greenhouse_var.get())
        lever_companies = split_board_names(self.lever_var.get())
        ashby_organizations = split_board_names(self.ashby_var.get())

        if not any(selected_sources.values()):
            messagebox.showerror(
                "No sources selected",
                "Please select at least one job source.",
            )
            return None

        ats_requirements = (
            ("greenhouse", greenhouse_boards, "Greenhouse board names"),
            ("lever", lever_companies, "Lever company names"),
            ("ashby", ashby_organizations, "Ashby organization names"),
        )
        for source_key, values, label in ats_requirements:
            if selected_sources.get(source_key) and not values:
                messagebox.showerror(
                    "Missing company boards",
                    f"{label} are required when {SOURCE_LABELS[source_key]} is selected.",
                )
                return None

        return (
            query,
            start_date,
            max_pages,
            output_path,
            selected_sources,
            greenhouse_boards,
            lever_companies,
            ashby_organizations,
        )

    def _start_scraping(self) -> None:
        values = self._validate_inputs()
        if values is None:
            return

        (
            query,
            start_date,
            max_pages,
            output_path,
            selected_sources,
            greenhouse_boards,
            lever_companies,
            ashby_organizations,
        ) = values
        self.output_var.set(str(output_path))
        self._clear_log()
        self._set_running(True)
        self._log("Starting scraper...")

        self.worker = threading.Thread(
            target=self._worker_run,
            args=(
                query,
                start_date,
                max_pages,
                output_path,
                selected_sources,
                greenhouse_boards,
                lever_companies,
                ashby_organizations,
            ),
            daemon=True,
        )
        self.worker.start()

    def _worker_run(
        self,
        query: str,
        start_date: date,
        max_pages: int,
        output_path: Path,
        selected_sources: dict[str, bool],
        greenhouse_boards: list[str],
        lever_companies: list[str],
        ashby_organizations: list[str],
    ) -> None:
        try:
            saved_path = run_scraper_workflow(
                query=query,
                start_date=start_date,
                max_pages=max_pages,
                output_filename=output_path,
                selected_sources=selected_sources,
                greenhouse_boards=greenhouse_boards,
                lever_companies=lever_companies,
                ashby_organizations=ashby_organizations,
                log=self._thread_log,
            )

            if saved_path is None:
                self.log_queue.put(("done", "Finished with no Excel file created."))
            else:
                self.log_queue.put(("done", f"Finished. Saved file: {saved_path}"))

        except ScraperError as exc:
            self.log_queue.put(("error", f"SCRAPER ERROR\n{'=' * 60}\n{exc}"))
        except Exception as exc:
            self.log_queue.put(
                ("error", f"Unexpected error: {type(exc).__name__}: {exc}")
            )

    def _thread_log(self, message: str) -> None:
        self.log_queue.put(("log", message))

    def _drain_log_queue(self) -> None:
        try:
            while True:
                kind, message = self.log_queue.get_nowait()

                if kind == "log":
                    self._log(message)
                elif kind == "done":
                    self._log(message)
                    self._set_running(False)
                    messagebox.showinfo("Scraping complete", message)
                elif kind == "error":
                    self._log(message)
                    self._set_running(False)
                    messagebox.showerror("Scraping failed", message)

        except queue.Empty:
            pass

        self.root.after(100, self._drain_log_queue)

    def _set_running(self, running: bool) -> None:
        if running:
            self.start_button.configure(state="disabled")
            self.status_var.set("Running...")
        else:
            self.start_button.configure(state="normal")
            self.status_var.set("Ready")

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


def main() -> int:
    root = tk.Tk()
    HiringCafeScraperApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
