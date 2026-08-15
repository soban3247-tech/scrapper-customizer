"""Explainable result produced when a job is compared with a profile."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .job import Job
from .profile import _unique_non_empty


class MatchResult(BaseModel):
    """A scored job together with evidence explaining the score."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    job: Job
    score: float = Field(ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1)
    component_scores: dict[str, float] = Field(default_factory=dict)

    @field_validator("matched_skills", "missing_skills")
    @classmethod
    def clean_skill_lists(cls, values: list[str]) -> list[str]:
        return _unique_non_empty(values)

    @field_validator("component_scores")
    @classmethod
    def validate_component_scores(cls, values: dict[str, float]) -> dict[str, float]:
        for name, score in values.items():
            if not name.strip():
                raise ValueError("component score names cannot be empty")
            if not 0 <= score <= 100:
                raise ValueError("component scores must be between 0 and 100")
        return values

    @model_validator(mode="after")
    def keep_skill_evidence_disjoint(self) -> "MatchResult":
        matched = {skill.casefold() for skill in self.matched_skills}
        overlap = [skill for skill in self.missing_skills if skill.casefold() in matched]
        if overlap:
            raise ValueError("a skill cannot be both matched and missing")
        return self

