"""Normalized job model shared by every scraper and downstream service."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Job(BaseModel):
    """A source-independent representation of a job vacancy."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    source: str = Field(min_length=1)
    source_job_id: str | None = None
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    description: str = ""
    location: str | None = None
    workplace_type: str | None = None
    commitment: str | None = None
    posted_date: date | None = None
    apply_url: HttpUrl
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_salary_range(self) -> "Job":
        """Reject a salary range whose upper bound is below its lower bound."""

        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_max < self.salary_min
        ):
            raise ValueError("salary_max must be greater than or equal to salary_min")
        return self

