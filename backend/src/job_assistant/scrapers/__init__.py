"""Common contracts, errors, and registry for job-source adapters."""

from .arbeitnow import ArbeitnowScraper
from .ashby import AshbyScraper
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
from .greenhouse import GreenhouseScraper
from .hiringcafe import HiringCafeScraper
from .lever import LeverScraper
from .remotive import RemotiveScraper
from .remote_ok import RemoteOkScraper
from .registry import ScraperRegistry
from .defaults import create_default_registry
from .service import (
    collect_jobs,
    deduplicate_jobs,
    filter_jobs_by_date,
    filter_jobs_by_preferences,
)

__all__ = [
    "ArbeitnowScraper",
    "AshbyScraper",
    "ConfigFieldKind",
    "JobScraper",
    "GreenhouseScraper",
    "HiringCafeScraper",
    "LeverScraper",
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
    "collect_jobs",
    "create_default_registry",
    "deduplicate_jobs",
    "filter_jobs_by_date",
    "filter_jobs_by_preferences",
]

