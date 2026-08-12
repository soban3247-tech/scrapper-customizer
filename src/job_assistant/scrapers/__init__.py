"""Common contracts, errors, and registry for job-source adapters."""

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
from .registry import ScraperRegistry

__all__ = [
    "ConfigFieldKind",
    "JobScraper",
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

