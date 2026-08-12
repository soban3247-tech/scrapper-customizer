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
    JobSource.HIRINGCAFE,
    JobSource.REMOTIVE,
    JobSource.ARBEITNOW,
    JobSource.REMOTE_OK,
]


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
    sources: list[JobSource] = Field(
        default_factory=lambda: list(DEFAULT_SOURCES),
        min_length=1,
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
    def remove_duplicate_sources(cls, values: list[JobSource]) -> list[JobSource]:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def require_selected_board_names(self) -> "SearchConfig":
        requirements = {
            JobSource.GREENHOUSE: (self.greenhouse_boards, "greenhouse_boards"),
            JobSource.LEVER: (self.lever_companies, "lever_companies"),
            JobSource.ASHBY: (self.ashby_organizations, "ashby_organizations"),
        }
        for source, (values, field_name) in requirements.items():
            if source in self.sources and not values:
                raise ValueError(f"{field_name} is required when {source.value} is selected")
        return self

