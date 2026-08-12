"""Common external contract for all platform-specific scraper adapters."""

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, computed_field

from job_assistant.models import Job, SearchConfig


class ConfigFieldKind(StrEnum):
    """Input controls the UI can render for platform-specific settings."""

    TEXT = "text"
    SECRET = "secret"
    STRING_LIST = "string_list"
    BOOLEAN = "boolean"
    INTEGER = "integer"


class ScraperConfigField(BaseModel):
    """Metadata describing one source-specific configuration value."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    key: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1)
    kind: ConfigFieldKind = ConfigFieldKind.TEXT
    required: bool = False
    help_text: str | None = None


class ScraperCapabilities(BaseModel):
    """Features and inputs exposed to the UI by a scraper adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    supports_pagination: bool = False
    supports_posted_after: bool = False
    supports_location: bool = False
    requires_browser: bool = False
    requires_credentials: bool = False
    configuration_fields: tuple[ScraperConfigField, ...] = ()


class ScraperDescriptor(BaseModel):
    """UI-safe description of a registered scraper."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    capabilities: ScraperCapabilities = Field(default_factory=ScraperCapabilities)


class ScraperIssue(BaseModel):
    """A non-crashing warning or error produced while scraping one source."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    code: str = Field(default="scraper_error", min_length=1)
    retryable: bool = False
    fatal: bool = False


class ScrapeResult(BaseModel):
    """Jobs and issues returned by one adapter without affecting other sources."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    jobs: list[Job] = Field(default_factory=list)
    issues: list[ScraperIssue] = Field(default_factory=list)

    @computed_field
    @property
    def succeeded(self) -> bool:
        return not any(issue.fatal for issue in self.issues)

    @classmethod
    def failure(
        cls,
        source_id: str,
        message: str,
        *,
        code: str = "scraper_error",
        retryable: bool = False,
    ) -> "ScrapeResult":
        return cls(
            source_id=source_id,
            issues=[
                ScraperIssue(
                    source_id=source_id,
                    message=message,
                    code=code,
                    retryable=retryable,
                    fatal=True,
                )
            ],
        )


@runtime_checkable
class JobScraper(Protocol):
    """Adapter boundary used by the registry, services, and future UI."""

    source_id: str
    display_name: str
    capabilities: ScraperCapabilities

    def search(self, config: SearchConfig) -> ScrapeResult:
        """Search one platform and return normalized jobs plus any issues."""
        ...

