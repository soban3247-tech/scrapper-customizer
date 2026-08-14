"""Editable Streamlit preview for an evidence-locked CV draft."""

from typing import Any

from job_assistant.customizer import (
    CvDraft,
    apply_cv_edits,
    render_cv_draft_text,
)


def render_editable_cv_preview(
    draft: CvDraft,
    *,
    streamlit_module: Any | None = None,
) -> CvDraft | None:
    """Render line-level edits and return only a fully validated preview."""

    st = streamlit_module or _load_streamlit()
    st.subheader("Editable CV preview")
    st.caption(
        "Relevant original-CV lines appear first. You may reorder words or make "
        "small wording changes, but new facts, skills, and numbers are blocked."
    )

    for warning in draft.warnings:
        st.warning(warning)

    edited_text_by_id: dict[str, str] = {}
    with st.form(f"cv_preview_form_{draft.draft_id}"):
        for section in draft.sections:
            st.markdown(f"#### {section.title}")
            for item in section.items:
                evidence = ", ".join(item.evidence_terms) or "Original CV line"
                edited_text_by_id[item.item_id] = st.text_area(
                    evidence,
                    value=item.draft_text,
                    key=f"cv_preview_{draft.draft_id}_{item.item_id}",
                    help=f"Source evidence: {item.original_text}",
                )
        submitted = st.form_submit_button(
            "Validate preview",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return None

    try:
        reviewed = apply_cv_edits(draft, edited_text_by_id)
    except (TypeError, ValueError) as exc:
        st.error(f"Preview was not accepted: {exc}")
        return None

    st.success("Preview validated against the original CV.")
    st.text_area(
        "Validated plain-text preview",
        value=render_cv_draft_text(reviewed),
        height=320,
        disabled=True,
    )
    return reviewed


def _load_streamlit() -> Any:
    import streamlit as st

    return st
