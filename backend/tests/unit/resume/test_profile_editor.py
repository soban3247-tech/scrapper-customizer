import pytest
from pydantic import ValidationError

from job_assistant.models import Profile
from job_assistant.resume import (
    profile_form_defaults,
    validate_profile_corrections,
    validation_error_messages,
)


def test_validates_and_normalizes_corrected_profile() -> None:
    profile = validate_profile_corrections(
        {
            "full_name": "  Malik Soban Rabbani  ",
            "skills": "Python, SQL; python\nDocker",
            "job_titles": "Backend Developer\nSoftware Engineer",
            "years_experience": "4.5",
            "education": "BS Computer Science, Example University\nMBA",
            "domain": " Software Engineering ",
            "preferred_locations": "Lahore, Remote",
            "remote_preference": "Yes",
        }
    )

    assert profile.full_name == "Malik Soban Rabbani"
    assert profile.skills == ["Python", "SQL", "Docker"]
    assert profile.job_titles == ["Backend Developer", "Software Engineer"]
    assert profile.years_experience == 4.5
    assert profile.education == [
        "BS Computer Science, Example University",
        "MBA",
    ]
    assert profile.domain == "Software Engineering"
    assert profile.preferred_locations == ["Lahore", "Remote"]
    assert profile.remote_preference is True


def test_converts_empty_optional_values_to_none() -> None:
    profile = validate_profile_corrections(
        {
            "full_name": " ",
            "years_experience": "",
            "domain": "\n",
            "remote_preference": "Not specified",
        }
    )

    assert profile.full_name is None
    assert profile.years_experience is None
    assert profile.domain is None
    assert profile.remote_preference is None


@pytest.mark.parametrize("years", ["not a number", "-2"])
def test_pydantic_rejects_invalid_experience_corrections(years: str) -> None:
    with pytest.raises(ValidationError):
        validate_profile_corrections({"years_experience": years})


def test_pydantic_rejects_unknown_form_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        validate_profile_corrections({"private_note": "must not be accepted"})


def test_serializes_profile_into_stable_form_defaults() -> None:
    defaults = profile_form_defaults(
        Profile(
            full_name="Malik Soban Rabbani",
            skills=["Python", "SQL"],
            job_titles=["Backend Developer", "Software Engineer"],
            years_experience=4,
            education=["BS Computer Science", "MBA"],
            domain="Software Engineering",
            preferred_locations=["Lahore", "Remote"],
            remote_preference=False,
        )
    )

    assert defaults == {
        "full_name": "Malik Soban Rabbani",
        "skills": "Python, SQL",
        "job_titles": "Backend Developer\nSoftware Engineer",
        "years_experience": "4",
        "education": "BS Computer Science\nMBA",
        "domain": "Software Engineering",
        "preferred_locations": "Lahore, Remote",
        "remote_preference": "No",
    }


def test_formats_pydantic_errors_for_the_ui() -> None:
    with pytest.raises(ValidationError) as captured:
        validate_profile_corrections({"years_experience": "invalid"})

    messages = validation_error_messages(captured.value)

    assert len(messages) == 1
    assert messages[0].startswith("Years experience:")
