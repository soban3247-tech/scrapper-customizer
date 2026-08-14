from datetime import date

import pytest
from pydantic import ValidationError

from job_assistant.models import Profile
from job_assistant.scrapers import (
    ConfigFieldKind,
    ScraperCapabilities,
    ScraperConfigField,
    ScraperDescriptor,
)
from ui.search_form import build_search_config, search_defaults


def descriptor(
    source_id: str,
    *fields: ScraperConfigField,
) -> ScraperDescriptor:
    return ScraperDescriptor(
        source_id=source_id,
        display_name=source_id,
        capabilities=ScraperCapabilities(configuration_fields=fields),
    )


def test_search_defaults_are_prefilled_from_confirmed_profile() -> None:
    profile = Profile(
        job_titles=["Backend Developer", "Software Engineer"],
        skills=["Python", "SQL"],
        preferred_locations=["Lahore", "Remote"],
        remote_preference=True,
    )

    defaults = search_defaults(profile, today=date(2026, 8, 14))

    assert defaults["query"] == "Backend Developer"
    assert defaults["skills"] == "Python, SQL"
    assert defaults["location"] == "Lahore"
    assert defaults["remote_only"] is True
    assert defaults["posted_after"] == date(2026, 7, 15)


def test_build_search_config_accepts_independent_sources_and_dynamic_options() -> None:
    descriptors = [
        descriptor("Public API"),
        descriptor(
            "Private API",
            ScraperConfigField(
                key="api_key",
                label="API key",
                kind=ConfigFieldKind.SECRET,
                required=True,
            ),
        ),
    ]

    config = build_search_config(
        query="Data Engineer",
        skills="Python, SQL\nPython",
        location="Remote",
        remote_only=True,
        posted_after=date(2026, 8, 1),
        max_pages=4,
        selected_sources=["Private API"],
        source_options={"Private API": {"api_key": "  secret-value  "}},
        descriptors=descriptors,
    )

    assert config.sources == ["Private API"]
    assert config.skills == ["Python", "SQL"]
    assert config.options_for("private api") == {"api_key": "secret-value"}


def test_build_search_config_rejects_missing_source_specific_value() -> None:
    descriptors = [
        descriptor(
            "Board Source",
            ScraperConfigField(
                key="boards",
                label="Board names",
                kind=ConfigFieldKind.STRING_LIST,
                required=True,
            ),
        )
    ]

    with pytest.raises(ValueError, match="Board names is required"):
        build_search_config(
            query="Developer",
            skills="",
            location="",
            remote_only=False,
            posted_after=date(2026, 8, 1),
            max_pages=1,
            selected_sources=["Board Source"],
            source_options={"Board Source": {"boards": []}},
            descriptors=descriptors,
        )


def test_build_search_config_requires_at_least_one_source() -> None:
    with pytest.raises(ValidationError):
        build_search_config(
            query="Developer",
            skills="",
            location="",
            remote_only=False,
            posted_after=date(2026, 8, 1),
            max_pages=1,
            selected_sources=[],
            source_options={},
            descriptors=[],
        )
