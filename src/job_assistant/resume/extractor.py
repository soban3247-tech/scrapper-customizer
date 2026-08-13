"""Explainable, local extraction of a validated profile from CV text."""

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from job_assistant.models import Profile

from .taxonomy import DOMAIN_RULES, SKILL_ALIASES, TITLE_ALIASES

_SENIORITY_PREFIXES = ("junior", "senior", "lead", "principal", "staff")
_DEGREE_PATTERN = re.compile(
    r"\b(?:"
    r"ph\.?d|doctor(?:ate|al)|master(?:'s)?|m\.?sc|m\.?s\.?|mba|"
    r"bachelor(?:'s)?|b\.?sc|b\.?s\.?|bba|bcs|associate(?:'s)?|"
    r"diploma"
    r")\b",
    re.IGNORECASE,
)
_EXPERIENCE_PATTERNS = (
    re.compile(
        r"\b(?:over|more\s+than|at\s+least)?\s*"
        r"(?P<years>\d{1,2}(?:\.\d+)?)\s*\+?\s*"
        r"(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexperience\s*(?:of|:)\s*"
        r"(?P<years>\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True, slots=True)
class ExtractionEvidence:
    """Auditable rule matches behind an extracted profile."""

    skill_matches: Mapping[str, tuple[str, ...]]
    title_matches: Mapping[str, tuple[str, ...]]
    experience_phrases: tuple[str, ...]
    education_lines: tuple[str, ...]
    domain_scores: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class ProfileExtraction:
    """A validated profile together with evidence suitable for UI review."""

    profile: Profile
    evidence: ExtractionEvidence


def extract_profile(text: str) -> Profile:
    """Return profile facts found by the local extraction rules."""

    return extract_profile_with_evidence(text).profile


def extract_profile_with_evidence(text: str) -> ProfileExtraction:
    """Return extracted facts and the exact rules that produced them."""

    normalized = _validate_text(text)
    skill_matches = _find_aliases(normalized, SKILL_ALIASES)
    title_matches = _find_titles(normalized)
    experience, experience_phrases = _find_experience(normalized)
    education = _find_education(normalized)
    domain, domain_scores = _find_domain(
        set(skill_matches),
        set(title_matches),
    )

    profile = Profile(
        skills=list(skill_matches),
        job_titles=list(title_matches),
        years_experience=experience,
        education=education,
        domain=domain,
    )
    evidence = ExtractionEvidence(
        skill_matches=_freeze_matches(skill_matches),
        title_matches=_freeze_matches(title_matches),
        experience_phrases=tuple(experience_phrases),
        education_lines=tuple(education),
        domain_scores=MappingProxyType(domain_scores),
    )
    return ProfileExtraction(profile=profile, evidence=evidence)


def _validate_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    normalized = text.strip()
    if not normalized:
        raise ValueError("CV text must not be empty")
    return normalized


def _find_aliases(
    text: str,
    aliases_by_name: Mapping[str, tuple[str, ...]],
) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for canonical, aliases in aliases_by_name.items():
        evidence: list[str] = []
        for alias in aliases:
            pattern = _term_pattern(alias)
            for match in pattern.finditer(text):
                value = match.group(0)
                if value.casefold() not in {item.casefold() for item in evidence}:
                    evidence.append(value)
        if evidence:
            matches[canonical] = evidence
    return matches


def _find_titles(text: str) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    prefix = rf"(?:(?:{'|'.join(_SENIORITY_PREFIXES)})\s+)?"
    for canonical, aliases in TITLE_ALIASES.items():
        evidence: list[str] = []
        for alias in aliases:
            pattern = re.compile(
                rf"(?<![A-Za-z0-9]){prefix}{re.escape(alias)}"
                rf"(?![A-Za-z0-9])",
                re.IGNORECASE,
            )
            for match in pattern.finditer(text):
                value = re.sub(r"\s+", " ", match.group(0)).strip()
                if value.casefold() not in {item.casefold() for item in evidence}:
                    evidence.append(value)
        if evidence:
            first = evidence[0].casefold()
            seniority = next(
                (
                    item.title()
                    for item in _SENIORITY_PREFIXES
                    if first.startswith(item)
                ),
                None,
            )
            title = f"{seniority} {canonical}" if seniority else canonical
            matches[title] = evidence
    return matches


def _find_experience(text: str) -> tuple[float | None, list[str]]:
    candidates: list[float] = []
    phrases: list[str] = []
    for pattern in _EXPERIENCE_PATTERNS:
        for match in pattern.finditer(text):
            years = float(match.group("years"))
            if years <= 60:
                candidates.append(years)
                phrases.append(match.group(0).strip())
    return (max(candidates) if candidates else None), phrases


def _find_education(text: str) -> list[str]:
    education: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = re.sub(r"^[\s\-•*|]+|[\s|]+$", "", raw_line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line or len(line) > 240 or not _DEGREE_PATTERN.search(line):
            continue
        key = line.casefold()
        if key not in seen:
            seen.add(key)
            education.append(line)
    return education


def _find_domain(
    skills: set[str],
    titles: set[str],
) -> tuple[str | None, dict[str, int]]:
    scores: dict[str, int] = {}
    for name, rule in DOMAIN_RULES.items():
        base_titles = {_without_seniority(title) for title in titles}
        scores[name] = len(skills & rule.skills) + 3 * len(base_titles & rule.titles)

    best_score = max(scores.values(), default=0)
    if best_score == 0:
        return None, scores
    winners = [name for name, score in scores.items() if score == best_score]
    return (winners[0] if len(winners) == 1 else None), scores


def _without_seniority(title: str) -> str:
    words = title.split(maxsplit=1)
    if len(words) == 2 and words[0].casefold() in _SENIORITY_PREFIXES:
        return words[1]
    return title


def _term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![A-Za-z0-9.]){re.escape(term)}(?![A-Za-z0-9])",
        re.IGNORECASE,
    )


def _freeze_matches(
    matches: Mapping[str, list[str]],
) -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType(
        {canonical: tuple(evidence) for canonical, evidence in matches.items()}
    )
