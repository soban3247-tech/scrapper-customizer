from datetime import date

from job_assistant.matching import rank_jobs, score_job
from job_assistant.models import Job, Profile, SearchConfig


TODAY = date(2026, 8, 14)


def profile() -> Profile:
    return Profile(
        skills=["Python", "SQL", "Docker"],
        job_titles=["Backend Developer"],
        domain="Software Engineering",
        preferred_locations=["Remote"],
        remote_preference=True,
    )


def config() -> SearchConfig:
    return SearchConfig(
        query="Backend Developer",
        location="Remote",
        remote_only=True,
        sources=["Example"],
    )


def job(
    title: str,
    description: str,
    url_id: str,
    *,
    location: str = "Remote",
    posted_date: date = date(2026, 8, 13),
) -> Job:
    return Job(
        source="Example",
        title=title,
        company="Example Ltd",
        description=description,
        location=location,
        posted_date=posted_date,
        apply_url=f"https://example.com/jobs/{url_id}",
    )


def test_strong_match_records_score_and_skill_evidence() -> None:
    result = score_job(
        job(
            "Senior Backend Developer",
            "Build REST APIs with Python, SQL, and Docker.",
            "strong",
        ),
        profile(),
        config(),
        today=TODAY,
    )

    assert result is not None
    assert result.score >= 85
    assert result.matched_skills == ["Python", "SQL", "Docker"]
    assert result.missing_skills == ["REST APIs"]
    assert "Title alignment" in result.explanation
    assert "missing skills: REST APIs" in result.explanation


def test_repeated_keywords_do_not_increase_the_score() -> None:
    single = score_job(
        job("Backend Developer", "Python", "single"),
        profile(),
        config(),
        today=TODAY,
    )
    repeated = score_job(
        job("Backend Developer", " ".join(["Python"] * 100), "repeated"),
        profile(),
        config(),
        today=TODAY,
    )

    assert single is not None
    assert repeated is not None
    assert repeated.score == single.score
    assert repeated.matched_skills == ["Python"]


def test_unrelated_job_is_removed() -> None:
    unrelated = job(
        "Financial Accountant",
        "Prepare tax reports and monthly financial statements.",
        "unrelated",
        location="Karachi",
    )

    assert score_job(unrelated, profile(), config(), today=TODAY) is None


def test_results_are_sorted_from_strong_to_weak() -> None:
    strong = job(
        "Backend Developer",
        "Python SQL Docker REST APIs",
        "strong",
    )
    weak = job(
        "Software Developer",
        "Python and Kubernetes",
        "weak",
        location="London",
        posted_date=date(2026, 7, 20),
    )
    unrelated = job("Office Administrator", "Calendar management", "none")

    results = rank_jobs(
        [weak, unrelated, strong],
        profile(),
        config(),
        today=TODAY,
    )

    assert [result.job.source_job_id for result in results] == [None, None]
    assert [str(result.job.apply_url) for result in results] == [
        "https://example.com/jobs/strong",
        "https://example.com/jobs/weak",
    ]
    assert results[0].score > results[1].score
