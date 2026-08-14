"""Deterministic job filtering, scoring, and ranking explanations."""

import re
from datetime import date
from typing import Iterable

from job_assistant.models import Job, MatchResult, Profile, SearchConfig
from job_assistant.resume.taxonomy import DOMAIN_RULES, SKILL_ALIASES, TITLE_ALIASES

COMPONENT_WEIGHTS = {
    "title": 35.0,
    "skills": 35.0,
    "domain": 15.0,
    "preferences": 10.0,
    "recency": 5.0,
}

_TITLE_NOISE = {"senior", "sr", "junior", "jr", "lead", "principal", "staff"}
_KNOWN_SKILLS_CASEFOLD = {skill.casefold() for skill in SKILL_ALIASES}


def rank_jobs(
    jobs: Iterable[Job],
    profile: Profile,
    config: SearchConfig,
    *,
    today: date | None = None,
) -> list[MatchResult]:
    """Remove unrelated jobs, score retained jobs, and sort best matches first."""

    results: list[MatchResult] = []
    for job in jobs:
        result = score_job(job, profile, config, today=today)
        if result is not None:
            results.append(result)
    return sorted(
        results,
        key=lambda result: (
            -result.score,
            -(result.job.posted_date.toordinal() if result.job.posted_date else 0),
            result.job.title.casefold(),
        ),
    )


def score_job(
    job: Job,
    profile: Profile,
    config: SearchConfig,
    *,
    today: date | None = None,
) -> MatchResult | None:
    """Return explainable evidence for one relevant job, or None if unrelated."""

    current_date = today or date.today()
    searchable_text = " ".join(
        value
        for value in (
            job.title,
            job.description,
            job.location or "",
            job.workplace_type or "",
            " ".join(job.tags),
        )
        if value
    )

    desired_titles = _unique([*profile.job_titles, config.query])
    title_score = _title_score(job.title, desired_titles)
    profile_skills = _unique([*profile.skills, *config.skills])
    matched_skills, missing_skills, job_skills = _skill_evidence(
        searchable_text,
        profile_skills,
    )
    skills_score = _skills_score(matched_skills, missing_skills)
    domain_score = _domain_score(
        profile.domain,
        job.title,
        searchable_text,
        job_skills,
    )

    if not (title_score >= 70 or matched_skills or domain_score > 0):
        return None

    preference_score, has_preferences = _preference_score(job, profile, config)
    recency_score = _recency_score(job.posted_date, current_date)
    components: dict[str, float] = {"title": title_score}
    applicable = {"title"}
    if profile_skills or job_skills:
        components["skills"] = skills_score
        applicable.add("skills")
    if profile.domain:
        components["domain"] = domain_score
        applicable.add("domain")
    if has_preferences:
        components["preferences"] = preference_score
        applicable.add("preferences")
    if job.posted_date is not None:
        components["recency"] = recency_score
        applicable.add("recency")

    score = _weighted_score(components, applicable)
    return MatchResult(
        job=job,
        score=score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        component_scores=components,
        explanation=_explanation(
            title_score=title_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            domain_score=domain_score if profile.domain else None,
            preference_score=preference_score if has_preferences else None,
            posted_date=job.posted_date,
            today=current_date,
        ),
    )


def _title_score(job_title: str, desired_titles: list[str]) -> float:
    job_tokens = _title_tokens(job_title)
    if not job_tokens:
        return 0.0
    scores: list[float] = []
    normalized_job = _normalize(job_title)
    for title in desired_titles:
        normalized_title = _normalize(title)
        if not normalized_title:
            continue
        if normalized_title in normalized_job or normalized_job in normalized_title:
            scores.append(100.0)
            continue
        desired_tokens = _title_tokens(title)
        if not desired_tokens:
            continue
        overlap = len(job_tokens & desired_tokens)
        coverage = overlap / len(desired_tokens)
        precision = overlap / len(job_tokens)
        scores.append(round((coverage * 0.7 + precision * 0.3) * 100, 1))
    return max(scores, default=0.0)


def _skill_evidence(
    text: str,
    profile_skills: list[str],
) -> tuple[list[str], list[str], set[str]]:
    job_skills = {
        canonical
        for canonical, aliases in SKILL_ALIASES.items()
        if any(_contains_term(text, alias) for alias in aliases)
    }
    canonical_profile: dict[str, str] = {}
    for skill in profile_skills:
        canonical = _canonical_skill(skill)
        canonical_profile[canonical.casefold()] = canonical
        if (
            canonical.casefold() not in _KNOWN_SKILLS_CASEFOLD
            and _contains_term(text, skill)
        ):
            job_skills.add(canonical)

    matched = [
        skill
        for skill in _ordered_skills(job_skills)
        if skill.casefold() in canonical_profile
    ]
    missing = [
        skill
        for skill in _ordered_skills(job_skills)
        if skill.casefold() not in canonical_profile
    ]
    return matched, missing, job_skills


def _skills_score(matched: list[str], missing: list[str]) -> float:
    total = len(matched) + len(missing)
    return round(100 * len(matched) / total, 1) if total else 0.0


def _domain_score(
    domain: str | None,
    job_title: str,
    text: str,
    job_skills: set[str],
) -> float:
    if not domain:
        return 0.0
    if _contains_term(text, domain):
        return 100.0
    rule = next(
        (rule for name, rule in DOMAIN_RULES.items() if name.casefold() == domain.casefold()),
        None,
    )
    if rule is None:
        return 0.0
    detected_titles = {
        canonical
        for canonical, aliases in TITLE_ALIASES.items()
        if any(_contains_term(job_title, alias) for alias in (canonical, *aliases))
    }
    if detected_titles & rule.titles:
        return 100.0
    evidence_count = len(job_skills & rule.skills)
    return min(90.0, 50.0 + evidence_count * 10.0) if evidence_count else 0.0


def _preference_score(
    job: Job,
    profile: Profile,
    config: SearchConfig,
) -> tuple[float, bool]:
    wants_remote = config.remote_only or profile.remote_preference is True
    locations = _unique(
        [config.location or "", *profile.preferred_locations]
    )
    has_preferences = wants_remote or bool(locations)
    if not has_preferences:
        return 0.0, False

    location_text = f"{job.location or ''} {job.workplace_type or ''}"
    checks: list[bool] = []
    if wants_remote:
        checks.append(_contains_term(location_text, "remote"))
    if locations:
        checks.append(
            any(_contains_term(location_text, location) for location in locations)
        )
    return round(100 * sum(checks) / len(checks), 1), True


def _recency_score(posted_date: date | None, today: date) -> float:
    if posted_date is None:
        return 0.0
    age = max(0, (today - posted_date).days)
    if age <= 3:
        return 100.0
    if age <= 7:
        return 85.0
    if age <= 14:
        return 70.0
    if age <= 30:
        return 50.0
    if age <= 60:
        return 25.0
    return 0.0


def _weighted_score(components: dict[str, float], applicable: set[str]) -> float:
    total_weight = sum(COMPONENT_WEIGHTS[name] for name in applicable)
    weighted = sum(
        components[name] * COMPONENT_WEIGHTS[name] for name in applicable
    )
    return round(weighted / total_weight, 1) if total_weight else 0.0


def _explanation(
    *,
    title_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
    domain_score: float | None,
    preference_score: float | None,
    posted_date: date | None,
    today: date,
) -> str:
    parts = [f"Title alignment: {title_score:.0f}%"]
    if matched_skills:
        parts.append(f"matched skills: {', '.join(matched_skills)}")
    if missing_skills:
        parts.append(f"missing skills: {', '.join(missing_skills)}")
    if domain_score is not None:
        parts.append(f"domain alignment: {domain_score:.0f}%")
    if preference_score is not None:
        parts.append(f"preference alignment: {preference_score:.0f}%")
    if posted_date is not None:
        age = max(0, (today - posted_date).days)
        parts.append("posted today" if age == 0 else f"posted {age} days ago")
    return "; ".join(parts) + "."


def _canonical_skill(value: str) -> str:
    requested = value.strip().casefold()
    for canonical, aliases in SKILL_ALIASES.items():
        if requested in {canonical.casefold(), *(alias.casefold() for alias in aliases)}:
            return canonical
    return value.strip()


def _ordered_skills(values: set[str]) -> list[str]:
    taxonomy_order = {name.casefold(): index for index, name in enumerate(SKILL_ALIASES)}
    return sorted(values, key=lambda value: (taxonomy_order.get(value.casefold(), 999), value))


def _title_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in _TITLE_NOISE
    }


def _contains_term(text: str, term: str) -> bool:
    cleaned = term.strip()
    if not cleaned:
        return False
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(cleaned)}(?![A-Za-z0-9])",
            text,
            re.IGNORECASE,
        )
    )


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result
