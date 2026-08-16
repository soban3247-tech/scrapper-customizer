"""Validated profile extracted from, and confirmed against, a user's CV."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _unique_non_empty(values: list[str]) -> list[str]:
    """Strip, remove empty values, and deduplicate without changing order."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


class Profile(BaseModel):
    """CV facts and editable preferences used for searching and matching."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    full_name: str | None = None
    skills: list[str] = Field(default_factory=list)
    job_titles: list[str] = Field(default_factory=list)
    years_experience: float | None = Field(default=None, ge=0)
    education: list[str] = Field(default_factory=list)
    domain: str | None = None
    preferred_locations: list[str] = Field(default_factory=list)
    remote_preference: bool | None = None

    @field_validator("skills", "job_titles", "education", "preferred_locations")
    @classmethod
    def clean_string_lists(cls, values: list[str]) -> list[str]:
        return _unique_non_empty(values)

