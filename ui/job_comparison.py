"""Streamlit presentation for evidence-only CV and job comparison."""

from typing import Any

from job_assistant.customizer import CvJobComparison


def render_job_comparison(
    comparison: CvJobComparison,
    *,
    cv_filename: str | None = None,
    streamlit_module: Any | None = None,
) -> None:
    """Show selected-job evidence without generating unsupported CV content."""

    st = streamlit_module or _load_streamlit()
    job = comparison.match.job

    st.header("CV and job comparison")
    st.subheader(f"{job.title} at {job.company}")
    st.caption(
        f"Ranked match: {comparison.match.score:g}/100"
        + (f" · CV: {cv_filename}" if cv_filename else "")
    )
    st.write(comparison.summary)

    skill_columns = st.columns(2)
    with skill_columns[0]:
        st.markdown("#### Supported by the original CV")
        if comparison.supported_skills:
            for skill in comparison.supported_skills:
                st.success(skill)
        else:
            st.info("No requested taxonomy skills were found in the original CV.")
    with skill_columns[1]:
        st.markdown("#### Missing from the original CV")
        if comparison.missing_skills:
            for skill in comparison.missing_skills:
                st.error(skill)
        else:
            st.success("No recognized requested skills are missing.")

    if comparison.profile_only_skills:
        st.warning(
            "The confirmed profile lists these skills, but they were not found in "
            "the uploaded CV text, so they are not treated as supported: "
            + ", ".join(comparison.profile_only_skills)
        )

    if comparison.required_years_experience is not None:
        required = comparison.required_years_experience
        cv_years = comparison.cv_years_experience
        confirmed = comparison.confirmed_years_experience
        if comparison.experience_requirement_met:
            st.success(
                f"Experience requirement: {required:g}+ years requested; "
                f"{cv_years:g} years supported by the original CV."
            )
        elif cv_years is None:
            st.warning(
                f"Experience requirement: {required:g}+ years requested; the "
                "original CV text does not verify a number of years."
            )
        else:
            st.error(
                f"Experience gap: {required:g}+ years requested; "
                f"{cv_years:g} years supported by the original CV."
            )
        if confirmed is not None and confirmed != cv_years:
            st.warning(
                f"The confirmed profile says {confirmed:g} years, but that value "
                "is not treated as CV evidence because the original text does not "
                "support the same number."
            )

    if comparison.relevant_profile_facts:
        st.markdown("#### Relevant confirmed profile facts")
        for fact in comparison.relevant_profile_facts:
            st.write(f"- {fact}")

    st.markdown("#### Relevant excerpts copied from the original CV")
    if comparison.relevant_cv_excerpts:
        for excerpt in comparison.relevant_cv_excerpts:
            st.code(excerpt.text, language=None)
            st.caption("Evidence: " + ", ".join(excerpt.matched_terms))
    else:
        st.info("No directly relevant CV lines were identified for this job.")

    st.caption(
        "This comparison only identifies existing evidence. It does not add or "
        "rewrite CV facts."
    )


def _load_streamlit() -> Any:
    import streamlit as st

    return st
