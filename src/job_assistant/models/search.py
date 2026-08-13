"""User-confirmed options for a multi-source job search."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .profile import _unique_non_empty


class JobSource(StrEnum):
    """Job sources supported by the MVP scraper registry."""

    HIRINGCAFE = "HiringCafe"
    REMOTIVE = "Remotive"
    ARBEITNOW = "Arbeitnow"
    REMOTE_OK = "Remote OK"
    GREENHOUSE = "Greenhouse"
    LEVER = "Lever"
    ASHBY = "Ashby"
    LINKEDIN = "LinkedIn"


DEFAULT_SOURCES = [
    JobSource.HIRINGCAFE.value,
    JobSource.REMOTIVE.value,
    JobSource.ARBEITNOW.value,
    JobSource.REMOTE_OK.value,
]

SourceOptionValue = str | int | float | bool | list[str]


class SearchConfig(BaseModel):
    """Search criteria validated before any scraper is called."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    query: str = Field(min_length=1)
    skills: list[str] = Field(default_factory=list)
    location: str | None = None
    remote_only: bool = False
    posted_after: date | None = None
    max_pages: int = Field(default=1, ge=1, le=25)
    sources: list[str] = Field(
        default_factory=lambda: list(DEFAULT_SOURCES),
        min_length=1,
    )
    source_options: dict[str, dict[str, SourceOptionValue]] = Field(
        default_factory=dict
    )
    greenhouse_boards: list[str] = Field(default_factory=list)
    lever_companies: list[str] = Field(default_factory=list)
    ashby_organizations: list[str] = Field(default_factory=list)

    @field_validator(
        "skills",
        "greenhouse_boards",
        "lever_companies",
        "ashby_organizations",
    )
    @classmethod
    def clean_string_lists(cls, values: list[str]) -> list[str]:
        return _unique_non_empty(values)

    @field_validator("sources")
    @classmethod
    def clean_sources(cls, values: list[str]) -> list[str]:
        return _unique_non_empty(values)

    @model_validator(mode="after")
    def require_selected_board_names(self) -> "SearchConfig":
        selected_sources = {source.casefold() for source in self.sources}
        requirements = {
            JobSource.GREENHOUSE.value: (
                self.greenhouse_boards,
                "greenhouse_boards",
                "boards",
            ),
            JobSource.LEVER.value: (
                self.lever_companies,
                "lever_companies",
                "companies",
            ),
            JobSource.ASHBY.value: (
                self.ashby_organizations,
                "ashby_organizations",
                "organizations",
            ),
        }
        for source, (legacy_values, field_name, option_key) in requirements.items():
            generic_values = self.options_for(source).get(option_key)
            has_generic_values = isinstance(generic_values, list) and bool(
                _unique_non_empty(generic_values)
            )
            if (
                source.casefold() in selected_sources
                and not legacy_values
                and not has_generic_values
            ):
                raise ValueError(f"{field_name} is required when {source} is selected")
        return self

    def options_for(self, source_id: str) -> dict[str, SourceOptionValue]:
        """Return generic adapter settings without hard-coding future platforms."""

        requested_key = source_id.strip().casefold()
        for configured_source, options in self.source_options.items():
            if configured_source.strip().casefold() == requested_key:
                return options
        return {}

