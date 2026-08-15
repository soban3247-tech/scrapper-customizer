from contextlib import nullcontext
from typing import Any

from job_assistant.models import Profile
from ui.profile_form import render_profile_form


class FakeStreamlit:
    def __init__(self, values: dict[str, Any], *, submitted: bool) -> None:
        self.values = values
        self.submitted = submitted
        self.errors: list[str] = []
        self.successes: list[str] = []

    def subheader(self, _message: str) -> None:
        pass

    def caption(self, _message: str) -> None:
        pass

    def form(self, _key: str):
        return nullcontext()

    def text_input(self, _label: str, *, value: str, key: str, **_kwargs) -> str:
        return self.values.get(key, value)

    def text_area(self, _label: str, *, value: str, key: str, **_kwargs) -> str:
        return self.values.get(key, value)

    def selectbox(
        self,
        _label: str,
        options: tuple[str, ...],
        *,
        index: int,
        key: str,
    ) -> str:
        return self.values.get(key, options[index])

    def form_submit_button(self, _label: str, **_kwargs) -> bool:
        return self.submitted

    def error(self, message: str) -> None:
        self.errors.append(message)

    def success(self, message: str) -> None:
        self.successes.append(message)


def test_form_returns_none_before_submission() -> None:
    st = FakeStreamlit({}, submitted=False)

    result = render_profile_form(Profile(skills=["Python"]), streamlit_module=st)

    assert result is None
    assert st.successes == []


def test_form_returns_the_confirmed_corrected_profile() -> None:
    st = FakeStreamlit(
        {
            "profile_skills": "Python, SQL",
            "profile_years_experience": "5",
            "profile_remote_preference": "Yes",
        },
        submitted=True,
    )

    result = render_profile_form(Profile(skills=["Python"]), streamlit_module=st)

    assert result is not None
    assert result.skills == ["Python", "SQL"]
    assert result.years_experience == 5
    assert result.remote_preference is True
    assert st.successes == ["Profile confirmed."]


def test_form_shows_pydantic_errors_without_returning_a_profile() -> None:
    st = FakeStreamlit(
        {"profile_years_experience": "five"},
        submitted=True,
    )

    result = render_profile_form(Profile(), streamlit_module=st)

    assert result is None
    assert len(st.errors) == 1
    assert st.errors[0].startswith("Years experience:")
    assert st.successes == []
