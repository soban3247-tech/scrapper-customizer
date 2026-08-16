"""API schemas for CV extraction and search suggestions."""

from pydantic import BaseModel, ConfigDict, Field

from job_assistant.models import Profile
from job_assistant.models.search import DEFAULT_SOURCES


class ResumeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    format: str
    page_count: int | None = None


class ExtractionEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_matches: dict[str, list[str]] = Field(default_factory=dict)
    title_matches: dict[str, list[str]] = Field(default_factory=dict)
    experience_phrases: list[str] = Field(default_factory=list)
    education_lines: list[str] = Field(default_factory=list)
    domain_scores: dict[str, int] = Field(default_factory=dict)


class SuggestedSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    skills: list[str] = Field(default_factory=list)
    location: str | None = None
    remote_only: bool = False
    sources: list[str] = Field(default_factory=lambda: list(DEFAULT_SOURCES))


class ProfileExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: ResumeMetadata
    profile: Profile
    evidence: ExtractionEvidenceResponse
    suggested_search: SuggestedSearch
