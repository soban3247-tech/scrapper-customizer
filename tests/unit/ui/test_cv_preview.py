from contextlib import nullcontext
from typing import Any

from job_assistant.customizer import CvDraft, compare_cv_to_job, create_cv_draft
from job_assistant.models import Job, MatchResult, Profile
from ui.cv_preview import render_editable_cv_preview


class FakeStreamlit:
    def __init__(self, values: dict[str, str], *, submitted: bool) -> None:
        self.values = values
        self.submitted = submitted
        self.errors: list[str] = []
        self.successes: list[str] = []
        self.warnings: list[str] = []

    def subheader(self, _message: str) -> None:
        pass

    def caption(self, _message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def markdown(self, _message: str) -> None:
        pass

    def form(self, _key: str):
        return nullcontext()

    def text_area(
        self,
        _label: str,
        *,
        value: str,
        key: str | None = None,
        **_kwargs: Any,
    ) -> str:
        return self.values.get(key, value) if key else value

    def form_submit_button(self, _label: str, **_kwargs: Any) -> bool:
        return self.submitted

    def error(self, message: str) -> None:
        self.errors.append(message)

    def success(self, message: str) -> None:
        self.successes.append(message)


def draft() -> CvDraft:
    original_cv = "Backend Developer\nBuilt Python APIs.\n4 years of experience."
    match = MatchResult(
        job=Job(
            source="Synthetic Jobs",
            title="Backend Developer",
            company="Example Company",
            description="Python and Docker are required.",
            apply_url="https://example.com/jobs/1",
        ),
        score=80,
        matched_skills=["Python"],
        missing_skills=["Docker"],
        explanation="Relevant title and Python skill.",
    )
    comparison = compare_cv_to_job(
        match,
        Profile(skills=["Python"], job_titles=["Backend Developer"]),
        original_cv,
    )
    return create_cv_draft(comparison, original_cv)


def test_preview_waits_for_user_validation() -> None:
    st = FakeStreamlit({}, submitted=False)

    result = render_editable_cv_preview(draft(), streamlit_module=st)

    assert result is None
    assert st.successes == []
    assert st.warnings == ["Missing CV skill: Docker"]


def test_preview_returns_a_validated_edit() -> None:
    current = draft()
    python_item = next(
        item for item in current.items if item.original_text == "Built Python APIs."
    )
    key = f"cv_preview_{current.draft_id}_{python_item.item_id}"
    st = FakeStreamlit({key: "Python APIs built."}, submitted=True)

    result = render_editable_cv_preview(current, streamlit_module=st)

    assert result is not None
    assert next(
        item.draft_text for item in result.items if item.item_id == python_item.item_id
    ) == "Python APIs built."
    assert st.errors == []
    assert st.successes == ["Preview validated against the original CV."]


def test_preview_shows_an_error_for_an_invented_skill() -> None:
    current = draft()
    python_item = next(
        item for item in current.items if item.original_text == "Built Python APIs."
    )
    key = f"cv_preview_{current.draft_id}_{python_item.item_id}"
    st = FakeStreamlit({key: "Built Python and Docker APIs."}, submitted=True)

    result = render_editable_cv_preview(current, streamlit_module=st)

    assert result is None
    assert len(st.errors) == 1
    assert "unsupported skills: Docker" in st.errors[0]
    assert st.successes == []
