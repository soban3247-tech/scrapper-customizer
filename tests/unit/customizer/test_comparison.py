from job_assistant.customizer import compare_cv_to_job
from job_assistant.models import Job, MatchResult, Profile


SYNTHETIC_CV = """
Malik Example
Backend Developer
Built Python REST APIs for an internal inventory platform.
Five projects delivered using SQL and Git.
5 years of professional experience in backend systems.
BS Computer Science, Example University
"""


def selected_match(description: str) -> MatchResult:
    return MatchResult(
        job=Job(
            source="Synthetic Jobs",
            title="Senior Backend Developer",
            company="Example Company",
            description=description,
            apply_url="https://example.com/jobs/backend",
        ),
        score=86,
        matched_skills=["Python"],
        missing_skills=["Docker", "Kubernetes"],
        explanation="Strong backend title and Python evidence.",
    )


def confirmed_profile() -> Profile:
    return Profile(
        skills=["Python", "SQL", "Docker"],
        job_titles=["Backend Developer"],
        years_experience=7,
        domain="Software Engineering",
    )


def test_comparison_uses_literal_cv_evidence_and_flags_missing_skills() -> None:
    comparison = compare_cv_to_job(
        selected_match(
            "Requires Python, Docker, Kubernetes, and 4+ years of "
            "professional experience."
        ),
        confirmed_profile(),
        SYNTHETIC_CV,
    )

    assert comparison.job_required_skills == ["Python", "Docker", "Kubernetes"]
    assert comparison.supported_skills == ["Python"]
    assert comparison.missing_skills == ["Docker", "Kubernetes"]
    assert comparison.profile_only_skills == ["Docker"]
    assert comparison.required_years_experience == 4
    assert comparison.cv_years_experience == 5
    assert comparison.confirmed_years_experience == 7
    assert comparison.experience_requirement_met is True

    normalized_cv_lines = {
        " ".join(line.split()) for line in SYNTHETIC_CV.splitlines() if line.strip()
    }
    assert comparison.relevant_cv_excerpts
    assert all(
        excerpt.text in normalized_cv_lines
        for excerpt in comparison.relevant_cv_excerpts
    )
    assert all(
        "Docker" not in excerpt.text and "Kubernetes" not in excerpt.text
        for excerpt in comparison.relevant_cv_excerpts
    )


def test_profile_only_experience_does_not_satisfy_job_requirement() -> None:
    comparison = compare_cv_to_job(
        selected_match("Python and 6+ years of professional experience required."),
        Profile(skills=["Python"], years_experience=8),
        "Backend Developer\nBuilt production services with Python.",
    )

    assert comparison.required_years_experience == 6
    assert comparison.cv_years_experience is None
    assert comparison.confirmed_years_experience == 8
    assert comparison.experience_requirement_met is False
    assert "not verified by the original CV" in comparison.summary


def test_unsupported_job_skills_are_never_reported_as_cv_supported() -> None:
    comparison = compare_cv_to_job(
        selected_match("Python, AWS, Terraform, and Kubernetes are required."),
        confirmed_profile(),
        SYNTHETIC_CV,
    )

    assert comparison.supported_skills == ["Python"]
    assert comparison.missing_skills == ["Kubernetes", "Terraform", "AWS"]
    assert set(comparison.supported_skills).isdisjoint(comparison.missing_skills)


def test_comparison_requires_original_cv_text() -> None:
    try:
        compare_cv_to_job(
            selected_match("Python required."),
            confirmed_profile(),
            "   ",
        )
    except ValueError as exc:
        assert "original CV text is required" in str(exc)
    else:
        raise AssertionError("empty original CV text should be rejected")
