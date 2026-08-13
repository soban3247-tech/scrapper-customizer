import pytest
from pydantic import ValidationError

from job_assistant.models import Profile


def test_profile_cleans_and_deduplicates_editable_lists() -> None:
    profile = Profile(
        full_name="  Malik Soban Rabbani  ",
        skills=[" Python ", "python", "", "SQL"],
        job_titles=["Backend Developer", "backend developer"],
        preferred_locations=["Lahore", " Lahore "],
    )

    assert profile.full_name == "Malik Soban Rabbani"
    assert profile.skills == ["Python", "SQL"]
    assert profile.job_titles == ["Backend Developer"]
    assert profile.preferred_locations == ["Lahore"]


def test_profile_defaults_to_empty_collections() -> None:
    first = Profile()
    second = Profile()

    first.skills.append("Python")

    assert second.skills == []


def test_profile_rejects_negative_experience() -> None:
    with pytest.raises(ValidationError):
        Profile(years_experience=-1)

