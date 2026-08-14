import pytest

from job_assistant.customizer import (
    CvJobComparison,
    UnsupportedCvEditError,
    apply_cv_edits,
    compare_cv_to_job,
    create_cv_draft,
    render_cv_draft_text,
)
from job_assistant.models import Job, MatchResult, Profile


SYNTHETIC_CV = """
Malik Example
Backend Developer
I built Python REST APIs & automated tests
Responsible for developing Python reporting tools
5 years of professional experience in backend systems.
BS Computer Science, Example University
"""


def comparison() -> CvJobComparison:
    match = MatchResult(
        job=Job(
            source="Synthetic Jobs",
            title="Senior Backend Developer",
            company="Example Company",
            description="Python, Docker, and 4+ years of experience are required.",
            apply_url="https://example.com/jobs/backend",
        ),
        score=88,
        matched_skills=["Python"],
        missing_skills=["Docker"],
        explanation="Strong title and Python evidence.",
    )
    return compare_cv_to_job(
        match,
        Profile(
            skills=["Python", "Docker"],
            job_titles=["Backend Developer"],
            years_experience=5,
        ),
        SYNTHETIC_CV,
    )


def test_draft_promotes_relevant_lines_and_only_rewords_source_content() -> None:
    draft = create_cv_draft(comparison(), SYNTHETIC_CV)

    assert [section.title for section in draft.sections] == [
        "Job-relevant CV content",
        "Other original CV content",
    ]
    assert [item.original_text for item in draft.items] == [
        "Backend Developer",
        "I built Python REST APIs & automated tests",
        "Responsible for developing Python reporting tools",
        "5 years of professional experience in backend systems.",
        "Malik Example",
        "BS Computer Science, Example University",
    ]
    assert draft.items[1].draft_text == "Built Python REST APIs and automated tests."
    assert draft.items[2].draft_text == "Developed Python reporting tools"
    assert draft.warnings == ["Missing CV skill: Docker"]

    preview = render_cv_draft_text(draft)
    assert preview.index("Backend Developer") < preview.index("Malik Example")


def test_supported_words_can_be_reordered_in_the_editable_preview() -> None:
    draft = create_cv_draft(comparison(), SYNTHETIC_CV)
    python_item = next(
        item for item in draft.items if item.original_text.startswith("I built Python")
    )

    reviewed = apply_cv_edits(
        draft,
        {
            python_item.item_id: "Built and automated Python REST APIs and tests.",
        },
    )

    reviewed_item = next(
        item for item in reviewed.items if item.item_id == python_item.item_id
    )
    assert reviewed_item.draft_text == (
        "Built and automated Python REST APIs and tests."
    )
    assert python_item.draft_text == "Built Python REST APIs and automated tests."


@pytest.mark.parametrize(
    ("unsafe_text", "message"),
    [
        ("Built Python and Docker APIs.", "unsupported skills: Docker"),
        ("Built 10 Python APIs.", "unsupported numeric claims: 10"),
        ("Built award-winning Python REST APIs.", "unsupported wording"),
    ],
)
def test_edits_cannot_add_unsupported_claims(
    unsafe_text: str,
    message: str,
) -> None:
    draft = create_cv_draft(comparison(), SYNTHETIC_CV)
    python_item = next(
        item for item in draft.items if item.original_text.startswith("I built Python")
    )

    with pytest.raises(UnsupportedCvEditError, match=message):
        apply_cv_edits(draft, {python_item.item_id: unsafe_text})


def test_experience_cannot_be_increased_or_added() -> None:
    draft = create_cv_draft(comparison(), SYNTHETIC_CV)
    experience_item = next(
        item for item in draft.items if item.original_text.startswith("5 years")
    )

    with pytest.raises(UnsupportedCvEditError, match="numeric claims: 8"):
        apply_cv_edits(
            draft,
            {experience_item.item_id: "8 years of professional experience."},
        )


def test_preview_rejects_blank_lines_and_unknown_item_ids() -> None:
    draft = create_cv_draft(comparison(), SYNTHETIC_CV)

    with pytest.raises(UnsupportedCvEditError, match="cannot be empty"):
        apply_cv_edits(draft, {draft.items[0].item_id: "  "})
    with pytest.raises(ValueError, match="unknown CV draft item IDs"):
        apply_cv_edits(draft, {"line-9999": "Unknown"})


def test_preview_cannot_remove_a_meaning_changing_qualifier() -> None:
    original_cv = "Backend Developer\nBasic Docker experience under supervision."
    match = MatchResult(
        job=Job(
            source="Synthetic Jobs",
            title="Backend Developer",
            company="Example Company",
            description="Docker experience is required.",
            apply_url="https://example.com/jobs/docker",
        ),
        score=70,
        matched_skills=["Docker"],
        explanation="Docker appears in the CV.",
    )
    compared = compare_cv_to_job(match, Profile(skills=["Docker"]), original_cv)
    draft = create_cv_draft(compared, original_cv)
    docker_item = next(item for item in draft.items if "Docker" in item.original_text)

    with pytest.raises(UnsupportedCvEditError, match="removes meaning-changing"):
        apply_cv_edits(draft, {docker_item.item_id: "Docker experience."})
