"""Normalization and Pydantic validation for user-corrected CV profiles."""

import re
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from job_assistant.models import Profile

_COMMA_LIST_FIELDS = frozenset(
    {"skills", "job_titles", "preferred_locations"}
)
_LIST_FIELDS = _COMMA_LIST_FIELDS | {"education"}
_REMOTE_VALUES = {
    "not specified": None,
    "yes": True,
    "no": False,
}


def validate_profile_corrections(values: Mapping[str, Any]) -> Profile:
    """Normalize editable form values and validate them as a Profile."""

    data = dict(values)
    for field in _LIST_FIELDS:
        if field in data:
            data[field] = _normalize_list(
                data[field],
                split_commas=field in _COMMA_LIST_FIELDS,
            )

    for field in ("full_name", "domain", "years_experience"):
        if field in data and isinstance(data[field], str):
            cleaned = data[field].strip()
            data[field] = cleaned or None

    if "remote_preference" in data:
        data["remote_preference"] = _normalize_remote_preference(
            data["remote_preference"]
        )

    return Profile.model_validate(data)


def profile_form_defaults(profile: Profile) -> dict[str, str]:
    """Serialize a Profile into editable text without losing list boundaries."""

    return {
        "full_name": profile.full_name or "",
        "skills": ", ".join(profile.skills),
        "job_titles": "\n".join(profile.job_titles),
        "years_experience": (
            _format_years(profile.years_experience)
            if profile.years_experience is not None
            else ""
        ),
        "education": "\n".join(profile.education),
        "domain": profile.domain or "",
        "preferred_locations": ", ".join(profile.preferred_locations),
        "remote_preference": _remote_label(profile.remote_preference),
    }


def validation_error_messages(error: ValidationError) -> list[str]:
    """Turn Pydantic details into concise messages suitable for a form."""

    messages: list[str] = []
    for detail in error.errors(include_url=False, include_context=False):
        location = " → ".join(str(part).replace("_", " ") for part in detail["loc"])
        label = location.capitalize() if location else "Profile"
        messages.append(f"{label}: {detail['msg']}")
    return messages


def _normalize_list(value: Any, *, split_commas: bool) -> Any:
    if not isinstance(value, str):
        return value
    separators = r"[\n;,]+" if split_commas else r"[\n;]+"
    return [item.strip() for item in re.split(separators, value) if item.strip()]


def _normalize_remote_preference(value: Any) -> Any:
    if isinstance(value, str):
        return _REMOTE_VALUES.get(value.strip().casefold(), value)
    return value


def _remote_label(value: bool | None) -> str:
    if value is None:
        return "Not specified"
    return "Yes" if value else "No"


def _format_years(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)
