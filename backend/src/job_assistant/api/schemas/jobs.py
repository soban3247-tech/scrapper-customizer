"""API schemas for normalized multi-source job searches."""

from pydantic import BaseModel, ConfigDict, Field

from job_assistant.models import Job
from job_assistant.scrapers import ScraperIssue


class JobSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[Job] = Field(default_factory=list)
    issues: list[ScraperIssue] = Field(default_factory=list)
    missing_date_count: int = Field(default=0, ge=0)
