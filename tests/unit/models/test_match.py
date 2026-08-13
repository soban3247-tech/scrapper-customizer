import pytest
from pydantic import ValidationError

from job_assistant.models import Job, MatchResult


@pytest.fixture
def job() -> Job:
    return Job(
        source="Remotive",
        title="Python Developer",
        company="Example Ltd",
        apply_url="https://example.com/jobs/123",
    )


def test_match_result_records_explainable_evidence(job: Job) -> None:
    result = MatchResult(
        job=job,
        score=82,
        matched_skills=["Python", " python ", "SQL"],
        missing_skills=["Docker"],
        explanation="Title matches and two required skills were found.",
        component_scores={"title": 100, "skills": 75},
    )

    assert result.score == 82
    assert result.matched_skills == ["Python", "SQL"]
    assert result.missing_skills == ["Docker"]


@pytest.mark.parametrize("score", [-0.1, 100.1])
def test_match_result_rejects_score_outside_percentage_range(
    job: Job, score: float
) -> None:
    with pytest.raises(ValidationError):
        MatchResult(job=job, score=score, explanation="Invalid score")


def test_match_result_rejects_invalid_component_score(job: Job) -> None:
    with pytest.raises(ValidationError, match="component scores"):
        MatchResult(
            job=job,
            score=50,
            explanation="Partial match",
            component_scores={"skills": 120},
        )


def test_match_result_rejects_skill_in_both_evidence_lists(job: Job) -> None:
    with pytest.raises(ValidationError, match="both matched and missing"):
        MatchResult(
            job=job,
            score=50,
            matched_skills=["Python"],
            missing_skills=["python"],
            explanation="Conflicting evidence",
        )

