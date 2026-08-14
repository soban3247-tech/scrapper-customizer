"""Truthful comparison of one ranked job with confirmed and original CV facts."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from job_assistant.models import MatchResult, Profile
from job_assistant.resume import extract_profile
from job_assistant.resume.taxonomy import SKILL_ALIASES


class CvEvidenceExcerpt(BaseModel):
    """An unchanged CV line and the evidence that made it relevant."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    text: str = Field(min_length=1)
    matched_terms: list[str] = Field(default_factory=list)

    @field_validator("matched_terms")
    @classmethod
    def clean_terms(cls, values: list[str]) -> list[str]:
        return _unique(values)


class CvJobComparison(BaseModel):
    """Evidence-only comparison that cannot introduce unsupported CV facts."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    match: MatchResult
    job_required_skills: list[str] = Field(default_factory=list)
    supported_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    profile_only_skills: list[str] = Field(default_factory=list)
    relevant_cv_excerpts: list[CvEvidenceExcerpt] = Field(default_factory=list)
    relevant_profile_facts: list[str] = Field(default_factory=list)
    required_years_experience: float | None = Field(default=None, ge=0)
    cv_years_experience: float | None = Field(default=None, ge=0)
    confirmed_years_experience: float | None = Field(default=None, ge=0)
    experience_requirement_met: bool | None = None
    summary: str = Field(min_length=1)

    @field_validator(
        "job_required_skills",
        "supported_skills",
        "missing_skills",
        "profile_only_skills",
        "relevant_profile_facts",
    )
    @classmethod
    def clean_lists(cls, values: list[str]) -> list[str]:
        return _unique(values)

    @model_validator(mode="after")
    def keep_supported_and_missing_skills_disjoint(self) -> "CvJobComparison":
        supported = {skill.casefold() for skill in self.supported_skills}
        if any(skill.casefold() in supported for skill in self.missing_skills):
            raise ValueError("a skill cannot be both supported and missing")
        return self


def compare_cv_to_job(
    match: MatchResult,
    profile: Profile,
    original_cv_text: str,
) -> CvJobComparison:
    """Compare a job with literal CV evidence and confirmed profile facts."""

    if not isinstance(match, MatchResult):
        raise TypeError("match must be a MatchResult")
    if not isinstance(profile, Profile):
        raise TypeError("profile must be a Profile")
    if not isinstance(original_cv_text, str):
        raise TypeError("original_cv_text must be a string")
    cv_text = original_cv_text.strip()
    if not cv_text:
        raise ValueError("original CV text is required for a truthful comparison")

    job = match.job
    job_text = " ".join([job.title, job.description, " ".join(job.tags)])
    required_skills = _skills_in_text(job_text)
    cv_skills = set(_skills_in_text(cv_text))
    profile_skills = {_canonical_skill(skill) for skill in profile.skills}

    supported_skills = [skill for skill in required_skills if skill in cv_skills]
    missing_skills = [skill for skill in required_skills if skill not in cv_skills]
    profile_only_skills = [
        skill
        for skill in missing_skills
        if skill in profile_skills
    ]

    required_years = _required_years(job_text)
    cv_years = extract_profile(cv_text).years_experience
    experience_met = _experience_requirement_met(
        required_years,
        cv_years,
    )
    excerpts = _relevant_excerpts(
        cv_text,
        job_title=job.title,
        supported_skills=supported_skills,
        include_experience=required_years is not None,
    )
    profile_facts = _relevant_profile_facts(
        profile,
        job_title=job.title,
        supported_skills=supported_skills,
        required_years=required_years,
    )

    return CvJobComparison(
        match=match,
        job_required_skills=required_skills,
        supported_skills=supported_skills,
        missing_skills=missing_skills,
        profile_only_skills=profile_only_skills,
        relevant_cv_excerpts=excerpts,
        relevant_profile_facts=profile_facts,
        required_years_experience=required_years,
        cv_years_experience=cv_years,
        confirmed_years_experience=profile.years_experience,
        experience_requirement_met=experience_met,
        summary=_summary(
            supported_skills,
            missing_skills,
            required_years,
            cv_years,
            experience_met,
        ),
    )


def _skills_in_text(text: str) -> list[str]:
    return [
        canonical
        for canonical, aliases in SKILL_ALIASES.items()
        if any(_contains_term(text, alias) for alias in aliases)
    ]


def _canonical_skill(value: str) -> str:
    requested = value.strip().casefold()
    for canonical, aliases in SKILL_ALIASES.items():
        if requested == canonical.casefold() or requested in {
            alias.casefold() for alias in aliases
        }:
            return canonical
    return value.strip()


def _required_years(text: str) -> float | None:
    patterns = (
        re.compile(
            r"\b(?P<years>\d{1,2}(?:\.\d+)?)\s*\+?\s*"
            r"(?:years?|yrs?)\s+(?:of\s+)?(?:[a-z-]+\s+){0,4}experience\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:minimum|min(?:imum)?\.?|at\s+least)\s+(?:of\s+)?"
            r"(?P<years>\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
            re.IGNORECASE,
        ),
    )
    values = [
        float(match.group("years"))
        for pattern in patterns
        for match in pattern.finditer(text)
        if float(match.group("years")) <= 60
    ]
    return max(values) if values else None


def _experience_requirement_met(
    required_years: float | None,
    cv_years: float | None,
) -> bool | None:
    if required_years is None:
        return None
    if cv_years is None:
        return False
    return cv_years >= required_years


def _relevant_excerpts(
    cv_text: str,
    *,
    job_title: str,
    supported_skills: list[str],
    include_experience: bool,
) -> list[CvEvidenceExcerpt]:
    title_terms = {
        term
        for term in re.findall(r"[a-z0-9]+", job_title.casefold())
        if len(term) >= 4 and term not in {"senior", "junior", "lead"}
    }
    excerpts: list[CvEvidenceExcerpt] = []
    seen: set[str] = set()
    for raw_line in cv_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or line.casefold() in seen:
            continue
        matched_terms = [
            skill for skill in supported_skills if _skill_in_text(line, skill)
        ]
        line_tokens = set(re.findall(r"[a-z0-9]+", line.casefold()))
        if title_terms & line_tokens:
            matched_terms.append("Job title")
        if include_experience and re.search(
            r"\b(?:years?|yrs?)\s+(?:of\s+)?(?:[a-z-]+\s+){0,4}experience\b",
            line,
            re.IGNORECASE,
        ):
            matched_terms.append("Experience")
        if not matched_terms:
            continue
        seen.add(line.casefold())
        excerpts.append(
            CvEvidenceExcerpt(text=line, matched_terms=_unique(matched_terms))
        )
        if len(excerpts) == 12:
            break
    return excerpts


def _relevant_profile_facts(
    profile: Profile,
    *,
    job_title: str,
    supported_skills: list[str],
    required_years: float | None,
) -> list[str]:
    facts: list[str] = []
    if supported_skills:
        facts.append(f"CV-supported skills: {', '.join(supported_skills)}")
    related_titles = [
        title
        for title in profile.job_titles
        if _title_overlap(title, job_title)
    ]
    if related_titles:
        facts.append(f"Confirmed job titles: {', '.join(related_titles)}")
    if profile.domain:
        facts.append(f"Confirmed career domain: {profile.domain}")
    if required_years is not None and profile.years_experience is not None:
        facts.append(f"Confirmed experience: {profile.years_experience:g} years")
    return facts


def _title_overlap(left: str, right: str) -> bool:
    left_terms = set(re.findall(r"[a-z0-9]+", left.casefold()))
    right_terms = set(re.findall(r"[a-z0-9]+", right.casefold()))
    return bool(left_terms & right_terms)


def _skill_in_text(text: str, canonical: str) -> bool:
    aliases = SKILL_ALIASES.get(canonical, (canonical,))
    return any(_contains_term(text, alias) for alias in aliases)


def _contains_term(text: str, term: str) -> bool:
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])",
            text,
            re.IGNORECASE,
        )
    )


def _summary(
    supported_skills: list[str],
    missing_skills: list[str],
    required_years: float | None,
    cv_years: float | None,
    experience_met: bool | None,
) -> str:
    parts = [
        f"{len(supported_skills)} requested skills are supported by the original CV"
    ]
    if missing_skills:
        parts.append(f"{len(missing_skills)} requested skills are missing")
    if required_years is not None:
        if experience_met:
            parts.append("the original CV experience meets the stated requirement")
        elif cv_years is None:
            parts.append("the experience requirement is not verified by the original CV")
        else:
            parts.append("the original CV experience is below the stated requirement")
    return "; ".join(parts) + "."


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result
