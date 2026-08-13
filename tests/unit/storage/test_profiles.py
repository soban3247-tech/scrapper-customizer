import sqlite3
from pathlib import Path

import pytest

from job_assistant.models import Profile
from job_assistant.storage import ProfileRepository, ProfileStorageError


@pytest.fixture
def repository(tmp_path: Path) -> ProfileRepository:
    return ProfileRepository(tmp_path / "nested" / "profiles.db")


def test_saves_and_loads_a_validated_profile(
    repository: ProfileRepository,
) -> None:
    profile = Profile(
        full_name="Malik Soban Rabbani",
        skills=["Python", "SQL"],
        job_titles=["Backend Developer"],
        years_experience=5.5,
        education=["BS Computer Science"],
        domain="Software Engineering",
        preferred_locations=["Lahore", "Remote"],
        remote_preference=True,
    )

    repository.save(profile)

    assert repository.load() == profile


def test_creates_the_parent_directory_and_database(tmp_path: Path) -> None:
    database_path = tmp_path / "new" / "directory" / "profiles.sqlite3"

    ProfileRepository(database_path)

    assert database_path.is_file()


def test_uses_configured_database_path_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "configured" / "profiles.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))

    repository = ProfileRepository()

    assert repository.database_path == database_path
    assert database_path.is_file()


def test_returns_none_when_a_profile_has_not_been_saved(
    repository: ProfileRepository,
) -> None:
    assert repository.load() is None


def test_updates_an_existing_profile(repository: ProfileRepository) -> None:
    repository.save(Profile(skills=["Python"]))

    repository.save(Profile(skills=["Python", "Docker"], domain="DevOps"))

    assert repository.load() == Profile(
        skills=["Python", "Docker"],
        domain="DevOps",
    )


def test_keeps_profiles_separate_by_key(repository: ProfileRepository) -> None:
    repository.save(Profile(full_name="First User"), profile_key="first")
    repository.save(Profile(full_name="Second User"), profile_key="second")

    assert repository.load(profile_key="first") == Profile(full_name="First User")
    assert repository.load(profile_key="second") == Profile(full_name="Second User")
    assert repository.load() is None


def test_deletes_a_saved_profile(repository: ProfileRepository) -> None:
    repository.save(Profile(skills=["Python"]))

    assert repository.delete() is True
    assert repository.delete() is False
    assert repository.load() is None


def test_rejects_empty_or_oversized_profile_keys(
    repository: ProfileRepository,
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        repository.save(Profile(), profile_key=" ")
    with pytest.raises(ValueError, match="100 characters"):
        repository.load(profile_key="x" * 101)


def test_does_not_interpolate_profile_keys_into_sql(
    repository: ProfileRepository,
) -> None:
    hostile_key = "'; DROP TABLE profiles; --"

    repository.save(Profile(full_name="Safe"), profile_key=hostile_key)

    assert repository.load(profile_key=hostile_key) == Profile(full_name="Safe")
    repository.save(Profile(full_name="Still safe"))
    assert repository.load() == Profile(full_name="Still safe")


def test_revalidates_stored_json_when_loading(
    repository: ProfileRepository,
) -> None:
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            """
            INSERT INTO profiles (profile_key, profile_json, updated_at)
            VALUES (?, ?, ?)
            """,
            ("broken", '{"years_experience": -5}', "2026-08-13T00:00:00+00:00"),
        )

    with pytest.raises(ProfileStorageError, match="saved profile is invalid"):
        repository.load(profile_key="broken")


def test_rejects_objects_that_are_not_profiles(
    repository: ProfileRepository,
) -> None:
    with pytest.raises(TypeError, match="must be a Profile"):
        repository.save({"skills": ["Python"]})  # type: ignore[arg-type]
