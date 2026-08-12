"""Common contracts, errors, and registry for job-source adapters."""

from .arbeitnow import ArbeitnowScraper
from .base import (
    ConfigFieldKind,
    JobScraper,
    ScrapeResult,
    ScraperCapabilities,
    ScraperConfigField,
    ScraperDescriptor,
    ScraperIssue,
)
from .errors import (
    ScraperConfigurationError,
    ScraperContractError,
    ScraperError,
    ScraperNotFoundError,
    ScraperRegistrationError,
    ScraperRequestError,
    ScraperResponseError,
)
from .remotive import RemotiveScraper
from .remote_ok import RemoteOkScraper
from .registry import ScraperRegistry

__all__ = [
    "ArbeitnowScraper",
    "ConfigFieldKind",
    "JobScraper",
    "RemotiveScraper",
    "RemoteOkScraper",
    "ScrapeResult",
    "ScraperCapabilities",
    "ScraperConfigField",
    "ScraperConfigurationError",
    "ScraperContractError",
    "ScraperDescriptor",
    "ScraperError",
    "ScraperIssue",
    "ScraperNotFoundError",
    "ScraperRegistrationError",
    "ScraperRegistry",
    "ScraperRequestError",
    "ScraperResponseError",
]

