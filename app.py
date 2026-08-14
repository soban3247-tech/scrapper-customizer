"""Streamlit entry point for CV confirmation and multi-source job search."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from job_assistant.models import Profile
from job_assistant.resume import ResumeReadError, extract_profile, read_resume_bytes
from job_assistant.scrapers import create_default_registry
from job_assistant.storage import ProfileRepository, ProfileStorageError
from ui.profile_form import render_profile_form
from ui.search_form import render_search_form
from ui.search_results import execute_search, render_search_result

EXTRACTED_PROFILE_KEY = "extracted_profile"
SEARCH_RESULT_KEY = "search_result"


def main() -> None:
    """Render the local-first Streamlit application."""

    load_dotenv()
    st.set_page_config(
        page_title="Job Scraper and CV Customizer",
        page_icon="🔎",
        layout="wide",
    )
    st.title("Job Scraper and CV Customizer")
    st.caption("Confirm your CV profile, then search several job sources at once.")

    repository = _profile_repository()
    confirmed_profile = _load_profile(repository)
    registry = create_default_registry()

    profile_tab, search_tab = st.tabs(["CV profile", "Job search"])
    with profile_tab:
        _render_profile_workflow(repository, confirmed_profile)

    with search_tab:
        config = render_search_form(confirmed_profile, registry)
        if config is not None:
            st.session_state[SEARCH_RESULT_KEY] = execute_search(registry, config)
        result = st.session_state.get(SEARCH_RESULT_KEY)
        if result is not None:
            render_search_result(result)


def _render_profile_workflow(
    repository: ProfileRepository,
    confirmed_profile: Profile | None,
) -> None:
    st.header("CV profile")
    st.write(
        "Upload a PDF or DOCX CV. Processing stays local, and only the confirmed "
        "profile fields are saved in SQLite."
    )
    uploaded_file = st.file_uploader("Upload your CV", type=("pdf", "docx"))
    if uploaded_file is not None and st.button("Extract profile from CV"):
        try:
            document = read_resume_bytes(uploaded_file.getvalue(), uploaded_file.name)
            st.session_state[EXTRACTED_PROFILE_KEY] = extract_profile(document.text)
            st.success("CV text was read. Review the extracted profile below.")
        except ResumeReadError as exc:
            st.error(str(exc))

    candidate = st.session_state.get(EXTRACTED_PROFILE_KEY, confirmed_profile)
    if candidate is None:
        st.info("Upload a CV to create a profile, or use the job-search form manually.")
        return

    corrected = render_profile_form(candidate, key_prefix="confirmed_profile")
    if corrected is None:
        return
    try:
        repository.save(corrected)
    except ProfileStorageError as exc:
        st.error(str(exc))
        return
    st.session_state.pop(EXTRACTED_PROFILE_KEY, None)
    st.session_state.pop(SEARCH_RESULT_KEY, None)
    st.success("Your confirmed profile was saved for future sessions.")
    st.rerun()


def _profile_repository() -> ProfileRepository:
    try:
        return ProfileRepository()
    except ProfileStorageError as exc:
        st.error(str(exc))
        st.stop()
        raise RuntimeError("Streamlit did not stop after a storage error") from exc


def _load_profile(repository: ProfileRepository) -> Profile | None:
    try:
        return repository.load()
    except ProfileStorageError as exc:
        st.error(str(exc))
        return None


if __name__ == "__main__":
    main()
