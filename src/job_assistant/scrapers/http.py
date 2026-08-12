"""Shared HTTP behavior for API-backed scraper adapters."""

from typing import Any

import requests

from .errors import ScraperRequestError, ScraperResponseError

DEFAULT_TIMEOUT_SECONDS = 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def create_session() -> requests.Session:
    """Create a consistently identified session for public job APIs."""

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": USER_AGENT,
        }
    )
    return session


def request_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
) -> Any:
    """Fetch JSON and translate transport/schema failures into shared errors."""

    try:
        response = session.get(
            url,
            params=params,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        raise ScraperRequestError(f"Request failed for {url}") from exc

    if response.status_code != 200:
        raise ScraperRequestError(
            f"HTTP {response.status_code} from {url}",
            retryable=response.status_code in {408, 425, 429, 500, 502, 503, 504},
        )

    try:
        return response.json()
    except (requests.exceptions.JSONDecodeError, ValueError) as exc:
        raise ScraperResponseError(f"Invalid JSON from {url}") from exc
