"""Runtime registry for selecting and safely executing scraper adapters."""

from collections.abc import Iterable

from pydantic import ValidationError

from job_assistant.models import SearchConfig

from .base import JobScraper, ScrapeResult, ScraperDescriptor
from .errors import (
    ScraperContractError,
    ScraperError,
    ScraperNotFoundError,
    ScraperRegistrationError,
)


def _registry_key(source_id: str) -> str:
    return source_id.strip().casefold()


class ScraperRegistry:
    """Discovers adapters by source name and isolates failures at runtime."""

    def __init__(self, scrapers: Iterable[JobScraper] = ()) -> None:
        self._scrapers: dict[str, JobScraper] = {}
        for scraper in scrapers:
            self.register(scraper)

    def register(self, scraper: JobScraper) -> None:
        """Register an adapter without coupling the registry to its platform."""

        if not isinstance(scraper, JobScraper):
            raise ScraperRegistrationError(
                "scraper must provide source_id, display_name, capabilities, and search()"
            )

        try:
            descriptor = ScraperDescriptor(
                source_id=scraper.source_id,
                display_name=scraper.display_name,
                capabilities=scraper.capabilities,
            )
        except (AttributeError, TypeError, ValidationError) as exc:
            raise ScraperRegistrationError(
                "scraper metadata does not satisfy the common contract"
            ) from exc

        key = _registry_key(descriptor.source_id)
        if key in self._scrapers:
            raise ScraperRegistrationError(
                f"scraper '{descriptor.source_id}' is already registered"
            )
        self._scrapers[key] = scraper

    def unregister(self, source_id: str) -> None:
        """Remove an adapter, allowing sources to be enabled or disabled at runtime."""

        key = _registry_key(source_id)
        if key not in self._scrapers:
            raise ScraperNotFoundError(f"scraper '{source_id}' is not registered")
        del self._scrapers[key]

    def get(self, source_id: str) -> JobScraper:
        """Return a registered adapter using a case-insensitive identifier."""

        try:
            return self._scrapers[_registry_key(source_id)]
        except KeyError as exc:
            raise ScraperNotFoundError(
                f"scraper '{source_id}' is not registered"
            ) from exc

    def descriptors(self) -> list[ScraperDescriptor]:
        """Return metadata the UI can use to build source controls dynamically."""

        return [
            ScraperDescriptor(
                source_id=scraper.source_id,
                display_name=scraper.display_name,
                capabilities=scraper.capabilities,
            )
            for scraper in self._scrapers.values()
        ]

    def run_selected(self, config: SearchConfig) -> list[ScrapeResult]:
        """Run selected adapters independently so one failure cannot stop others."""

        return [self._run_one(source_id, config) for source_id in config.sources]

    def _run_one(self, source_id: str, config: SearchConfig) -> ScrapeResult:
        try:
            scraper = self.get(source_id)
            result = scraper.search(config)
            if not isinstance(result, ScrapeResult):
                raise ScraperContractError(
                    f"scraper '{source_id}' returned {type(result).__name__}, not ScrapeResult"
                )
            if _registry_key(result.source_id) != _registry_key(scraper.source_id):
                raise ScraperContractError(
                    f"scraper '{source_id}' returned a result for '{result.source_id}'"
                )
            return result
        except ScraperError as exc:
            return ScrapeResult.failure(
                source_id,
                str(exc),
                code=exc.code,
                retryable=exc.retryable,
            )
        except Exception:
            return ScrapeResult.failure(
                source_id,
                f"scraper '{source_id}' failed unexpectedly",
                code="unexpected_error",
            )
