"""Dynamic Streamlit form for configuring a multi-source job search."""

import re
from datetime import date, timedelta
from typing import Any

from pydantic import ValidationError

from job_assistant.models import DEFAULT_SOURCES, Profile, SearchConfig
from job_assistant.scrapers import (
    ConfigFieldKind,
    ScraperConfigField,
    ScraperDescriptor,
    ScraperRegistry,
)


def search_defaults(
    profile: Profile | None,
    *,
    today: date | None = None,
) -> dict[str, object]:
    """Build editable search defaults from the user's confirmed profile."""

    current_date = today or date.today()
    if profile is None:
        return {
            "query": "",
            "skills": "",
            "location": "",
            "remote_only": False,
            "posted_after": current_date - timedelta(days=30),
            "max_pages": 3,
        }

    query = next(iter(profile.job_titles), profile.domain or "")
    return {
        "query": query,
        "skills": ", ".join(profile.skills),
        "location": next(iter(profile.preferred_locations), ""),
        "remote_only": bool(profile.remote_preference),
        "posted_after": current_date - timedelta(days=30),
        "max_pages": 3,
    }


def build_search_config(
    *,
    query: str,
    skills: str | list[str],
    location: str,
    remote_only: bool,
    posted_after: date,
    max_pages: int,
    selected_sources: list[str],
    source_options: dict[str, dict[str, object]],
    descriptors: list[ScraperDescriptor],
) -> SearchConfig:
    """Validate common and adapter-specific values before scraping begins."""

    descriptor_by_id = {
        descriptor.source_id.casefold(): descriptor for descriptor in descriptors
    }
    cleaned_options: dict[str, dict[str, object]] = {}
    for source_id in selected_sources:
        descriptor = descriptor_by_id.get(source_id.casefold())
        if descriptor is None:
            raise ValueError(f"Unknown job source: {source_id}")
        options = source_options.get(source_id, {})
        cleaned_options[source_id] = _validate_source_options(descriptor, options)

    return SearchConfig(
        query=query,
        skills=_split_values(skills) if isinstance(skills, str) else skills,
        location=location or None,
        remote_only=remote_only,
        posted_after=posted_after,
        max_pages=max_pages,
        sources=selected_sources,
        source_options=cleaned_options,
    )


def render_search_form(
    profile: Profile | None,
    registry: ScraperRegistry,
    *,
    streamlit_module: Any | None = None,
) -> SearchConfig | None:
    """Render editable common/source fields and return a submitted config."""

    st = streamlit_module or _load_streamlit()
    defaults = search_defaults(profile)
    descriptors = registry.descriptors()
    default_sources = {
        source.casefold() for source in DEFAULT_SOURCES
    }

    st.header("Search for jobs")
    if profile is None:
        st.info(
            "No confirmed profile is saved yet. You can still enter the search "
            "details manually."
        )
    else:
        st.caption("Search fields were prefilled from your confirmed profile.")

    query = st.text_input("Job title", value=str(defaults["query"]))
    skills = st.text_area(
        "Skills",
        value=str(defaults["skills"]),
        help="Separate skills with commas or new lines.",
    )
    location = st.text_input("Location", value=str(defaults["location"]))

    common_columns = st.columns(3)
    remote_only = common_columns[0].checkbox(
        "Remote jobs only",
        value=bool(defaults["remote_only"]),
    )
    posted_after = common_columns[1].date_input(
        "Posted on or after",
        value=defaults["posted_after"],
        max_value=date.today(),
    )
    max_pages = common_columns[2].number_input(
        "Maximum pages",
        min_value=1,
        max_value=25,
        value=int(defaults["max_pages"]),
        step=1,
    )

    st.subheader("Job sources")
    selected_sources: list[str] = []
    source_options: dict[str, dict[str, object]] = {}
    source_columns = st.columns(2)
    for index, descriptor in enumerate(descriptors):
        enabled = source_columns[index % 2].checkbox(
            descriptor.display_name,
            value=descriptor.source_id.casefold() in default_sources,
            key=f"source_{descriptor.source_id}",
        )
        if not enabled:
            continue
        selected_sources.append(descriptor.source_id)
        if descriptor.capabilities.configuration_fields:
            with st.expander(f"{descriptor.display_name} settings", expanded=True):
                source_options[descriptor.source_id] = {
                    field.key: _render_configuration_field(st, descriptor, field)
                    for field in descriptor.capabilities.configuration_fields
                }

    submitted = st.button("Run job search", type="primary", use_container_width=True)
    if not submitted:
        return None

    try:
        return build_search_config(
            query=query,
            skills=skills,
            location=location,
            remote_only=remote_only,
            posted_after=posted_after,
            max_pages=int(max_pages),
            selected_sources=selected_sources,
            source_options=source_options,
            descriptors=descriptors,
        )
    except (ValidationError, ValueError) as exc:
        st.error(_friendly_error(exc))
        return None


def _render_configuration_field(
    st: Any,
    descriptor: ScraperDescriptor,
    field: ScraperConfigField,
) -> object:
    key = f"source_option_{descriptor.source_id}_{field.key}"
    if field.kind is ConfigFieldKind.STRING_LIST:
        value = st.text_area(
            field.label,
            key=key,
            help=field.help_text,
            placeholder="One per line, or separated by commas",
        )
        return _split_values(value)
    if field.kind is ConfigFieldKind.SECRET:
        return st.text_input(
            field.label,
            key=key,
            help=field.help_text,
            type="password",
        )
    if field.kind is ConfigFieldKind.BOOLEAN:
        return st.checkbox(field.label, key=key, help=field.help_text)
    if field.kind is ConfigFieldKind.INTEGER:
        return int(
            st.number_input(
                field.label,
                key=key,
                help=field.help_text,
                min_value=1,
                step=1,
            )
        )
    return st.text_input(field.label, key=key, help=field.help_text)


def _validate_source_options(
    descriptor: ScraperDescriptor,
    options: dict[str, object],
) -> dict[str, object]:
    validated: dict[str, object] = {}
    for field in descriptor.capabilities.configuration_fields:
        value = options.get(field.key)
        if isinstance(value, str):
            value = value.strip()
        elif isinstance(value, list):
            value = _split_values(value)
        if field.required and value in (None, "", [], False):
            raise ValueError(
                f"{field.label} is required when {descriptor.display_name} is selected."
            )
        if value not in (None, "", []):
            validated[field.key] = value
    return validated


def _split_values(values: str | list[object]) -> list[str]:
    raw_values = values if isinstance(values, list) else re.split(r"[\n,;]+", values)
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        item = str(value).strip().strip("/")
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            cleaned.append(item)
    return cleaned


def _friendly_error(error: ValidationError | ValueError) -> str:
    if isinstance(error, ValidationError):
        messages = [item["msg"].removeprefix("Value error, ") for item in error.errors()]
        return "Please correct the search form: " + "; ".join(messages)
    return str(error)


def _load_streamlit() -> Any:
    import streamlit as st

    return st
