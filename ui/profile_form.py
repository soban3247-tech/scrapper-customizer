"""Streamlit form for reviewing and correcting an extracted CV profile."""

from typing import Any

from pydantic import ValidationError

from job_assistant.models import Profile
from job_assistant.resume.profile_editor import (
    profile_form_defaults,
    validate_profile_corrections,
    validation_error_messages,
)

REMOTE_OPTIONS = ("Not specified", "Yes", "No")


def render_profile_form(
    profile: Profile,
    *,
    key_prefix: str = "profile",
    streamlit_module: Any | None = None,
) -> Profile | None:
    """Render an editable profile and return it after successful submission."""

    st = streamlit_module or _load_streamlit()
    defaults = profile_form_defaults(profile)

    st.subheader("Review your extracted profile")
    st.caption(
        "Correct anything that was not detected accurately before continuing."
    )

    with st.form(f"{key_prefix}_form"):
        full_name = st.text_input(
            "Full name",
            value=defaults["full_name"],
            key=f"{key_prefix}_full_name",
        )
        skills = st.text_area(
            "Skills",
            value=defaults["skills"],
            help="Separate skills with commas or new lines.",
            key=f"{key_prefix}_skills",
        )
        job_titles = st.text_area(
            "Job titles",
            value=defaults["job_titles"],
            help="Enter one title per line, or separate titles with commas.",
            key=f"{key_prefix}_job_titles",
        )
        years_experience = st.text_input(
            "Years of experience",
            value=defaults["years_experience"],
            help="Leave blank when it is not known.",
            key=f"{key_prefix}_years_experience",
        )
        education = st.text_area(
            "Education",
            value=defaults["education"],
            help="Enter one qualification per line.",
            key=f"{key_prefix}_education",
        )
        domain = st.text_input(
            "Likely career domain",
            value=defaults["domain"],
            key=f"{key_prefix}_domain",
        )
        preferred_locations = st.text_input(
            "Preferred locations",
            value=defaults["preferred_locations"],
            help="Separate locations with commas.",
            key=f"{key_prefix}_preferred_locations",
        )
        remote_preference = st.selectbox(
            "Prefer remote work?",
            REMOTE_OPTIONS,
            index=REMOTE_OPTIONS.index(defaults["remote_preference"]),
            key=f"{key_prefix}_remote_preference",
        )
        submitted = st.form_submit_button("Confirm profile", type="primary")

    if not submitted:
        return None

    try:
        corrected = validate_profile_corrections(
            {
                "full_name": full_name,
                "skills": skills,
                "job_titles": job_titles,
                "years_experience": years_experience,
                "education": education,
                "domain": domain,
                "preferred_locations": preferred_locations,
                "remote_preference": remote_preference,
            }
        )
    except ValidationError as error:
        for message in validation_error_messages(error):
            st.error(message)
        return None

    st.success("Profile confirmed.")
    return corrected


def _load_streamlit() -> Any:
    import streamlit as st

    return st
