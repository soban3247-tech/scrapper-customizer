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

from job_assistant.customizer import CvDraft, compare_cv_to_job, create_cv_draft
from job_assistant.matching import rank_jobs
from job_assistant.models import MatchResult, Profile
from job_assistant.resume import ResumeReadError, extract_profile, read_resume_bytes
from job_assistant.scrapers import create_default_registry
from job_assistant.storage import (
    ProfileRepository,
    ProfileStorageError,
    SearchResultRepository,
    SearchResultStorageError,
)
from ui.cv_preview import render_editable_cv_preview
from ui.job_comparison import render_job_comparison
from ui.profile_form import render_profile_form
from ui.search_form import render_search_form
from ui.search_results import execute_search, render_search_result

EXTRACTED_PROFILE_KEY = "extracted_profile"
SEARCH_RESULT_KEY = "search_result"
SEARCH_ID_KEY = "search_id"
ORIGINAL_CV_TEXT_KEY = "original_cv_text"
ORIGINAL_CV_FILENAME_KEY = "original_cv_filename"
SELECTED_MATCH_KEY = "selected_match"
CV_DRAFT_KEY = "cv_draft"
REVIEWED_CV_DRAFT_KEY = "reviewed_cv_draft"


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

    profile_tab, search_tab, customization_tab = st.tabs(
        ["CV profile", "Job search", "CV customization"]
    )
    with profile_tab:
        _render_profile_workflow(repository, confirmed_profile)

    with search_tab:
        config = render_search_form(confirmed_profile, registry)
        if config is not None:
            st.session_state.pop(SELECTED_MATCH_KEY, None)
            _clear_customization_draft()
            raw_result = execute_search(registry, config)
            ranking_profile = confirmed_profile or Profile()
            ranked_result = raw_result.model_copy(
                update={
                    "matches": rank_jobs(
                        raw_result.jobs,
                        ranking_profile,
                        config,
                    )
                }
            )
            st.session_state[SEARCH_RESULT_KEY] = ranked_result
            st.session_state.pop(SEARCH_ID_KEY, None)
            try:
                st.session_state[SEARCH_ID_KEY] = SearchResultRepository().save(
                    config,
                    ranked_result.matches,
                )
            except SearchResultStorageError as exc:
                st.warning(str(exc))
        result = st.session_state.get(SEARCH_RESULT_KEY)
        if result is not None:
            search_id = st.session_state.get(SEARCH_ID_KEY)
            if search_id is not None:
                st.caption(f"Saved locally as search #{search_id}.")
            selected_match = render_search_result(result)
            if selected_match is not None:
                if st.session_state.get(SELECTED_MATCH_KEY) != selected_match:
                    _clear_customization_draft()
                st.session_state[SELECTED_MATCH_KEY] = selected_match

    with customization_tab:
        _render_customization_workflow(confirmed_profile)


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
        st.session_state.pop(EXTRACTED_PROFILE_KEY, None)
        st.session_state.pop(ORIGINAL_CV_TEXT_KEY, None)
        st.session_state.pop(ORIGINAL_CV_FILENAME_KEY, None)
        st.session_state.pop(SEARCH_RESULT_KEY, None)
        st.session_state.pop(SEARCH_ID_KEY, None)
        st.session_state.pop(SELECTED_MATCH_KEY, None)
        _clear_customization_draft()
        try:
            document = read_resume_bytes(uploaded_file.getvalue(), uploaded_file.name)
            st.session_state[EXTRACTED_PROFILE_KEY] = extract_profile(document.text)
            st.session_state[ORIGINAL_CV_TEXT_KEY] = document.text
            st.session_state[ORIGINAL_CV_FILENAME_KEY] = document.filename
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
    st.session_state.pop(SEARCH_ID_KEY, None)
    st.session_state.pop(SELECTED_MATCH_KEY, None)
    _clear_customization_draft()
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


def _render_customization_workflow(confirmed_profile: Profile | None) -> None:
    selected_match = st.session_state.get(SELECTED_MATCH_KEY)
    if not isinstance(selected_match, MatchResult):
        st.header("CV customization")
        st.info("Select one ranked job in the Job search results table first.")
        return
    if confirmed_profile is None:
        st.header("CV customization")
        st.info("Confirm your CV profile before comparing it with a selected job.")
        return

    original_cv_text = st.session_state.get(ORIGINAL_CV_TEXT_KEY)
    if not isinstance(original_cv_text, str) or not original_cv_text.strip():
        st.header("CV customization")
        st.info(
            "Upload the original CV again in the CV profile tab. For privacy, "
            "the original CV text is kept only for the active app session."
        )
        return

    comparison = compare_cv_to_job(
        selected_match,
        confirmed_profile,
        original_cv_text,
    )
    render_job_comparison(
        comparison,
        cv_filename=st.session_state.get(ORIGINAL_CV_FILENAME_KEY),
    )
    generated_draft = create_cv_draft(comparison, original_cv_text)
    stored_draft = st.session_state.get(CV_DRAFT_KEY)
    if not isinstance(stored_draft, CvDraft) or (
        stored_draft.draft_id != generated_draft.draft_id
    ):
        st.session_state[CV_DRAFT_KEY] = generated_draft
        st.session_state.pop(REVIEWED_CV_DRAFT_KEY, None)
        stored_draft = generated_draft

    reviewed_draft = st.session_state.get(REVIEWED_CV_DRAFT_KEY)
    active_draft = (
        reviewed_draft
        if isinstance(reviewed_draft, CvDraft)
        and reviewed_draft.draft_id == stored_draft.draft_id
        else stored_draft
    )
    reviewed = render_editable_cv_preview(active_draft)
    if reviewed is not None:
        st.session_state[REVIEWED_CV_DRAFT_KEY] = reviewed


def _clear_customization_draft() -> None:
    st.session_state.pop(CV_DRAFT_KEY, None)
    st.session_state.pop(REVIEWED_CV_DRAFT_KEY, None)


if __name__ == "__main__":
    main()
