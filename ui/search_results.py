"""Streamlit progress and raw results for a multi-source job search."""

from io import BytesIO
from typing import Any

import pandas as pd

from job_assistant.models import MatchResult, SearchConfig
from job_assistant.scrapers import ScraperRegistry
from job_assistant.search import (
    SearchProgress,
    SearchProgressStatus,
    SearchRunResult,
    run_search,
)


def execute_search(
    registry: ScraperRegistry,
    config: SearchConfig,
    *,
    streamlit_module: Any | None = None,
) -> SearchRunResult:
    """Run the configured search while updating visible source progress."""

    st = streamlit_module or _load_streamlit()
    progress_bar = st.progress(0.0, text="Preparing job search...")

    def show_progress(event: SearchProgress) -> None:
        completed = event.source_number - (
            1 if event.status is SearchProgressStatus.STARTED else 0
        )
        fraction = completed / event.source_count
        if event.status is SearchProgressStatus.STARTED:
            message = f"Searching {event.source_id}..."
        elif event.status is SearchProgressStatus.FAILED:
            message = f"{event.source_id} failed; continuing with other sources."
        else:
            message = f"{event.source_id} completed with {event.job_count} jobs."
        progress_bar.progress(fraction, text=message)

    result = run_search(registry, config, on_progress=show_progress)
    progress_bar.progress(1.0, text="Search complete.")
    return result


def render_search_result(
    result: SearchRunResult,
    *,
    streamlit_module: Any | None = None,
) -> None:
    """Display source outcomes, searchable ranked jobs, and safe exports."""

    st = streamlit_module or _load_streamlit()
    st.subheader("Search results")

    source_columns = st.columns(max(1, min(4, len(result.source_results))))
    for index, source_result in enumerate(result.source_results):
        label = source_result.source_id
        if not source_result.succeeded:
            label += " (failed)"
        source_columns[index % len(source_columns)].metric(
            label,
            len(source_result.jobs),
        )

    for issue in result.issues:
        message = f"{issue.source_id}: {issue.message}"
        if issue.fatal:
            st.error(message)
        else:
            st.warning(message)
    if result.jobs_without_dates:
        st.warning(
            f"Skipped {result.jobs_without_dates} jobs because their sources did "
            "not provide a recognizable posting date."
        )

    if not result.jobs:
        st.info("No jobs matched the selected search and date range.")
        return

    if not result.matches:
        st.info("No jobs had a meaningful title, domain, or skill relationship.")
        return

    filter_text = st.text_input(
        "Filter displayed results",
        placeholder="Search title, company, location, source, or skill",
    )
    displayed_matches = filter_matches(result.matches, filter_text)
    if not displayed_matches:
        st.info("No ranked results match this table filter.")
        return

    rows = [_match_row(match) for match in displayed_matches]
    st.caption(f"Showing {len(rows)} of {len(result.matches)} ranked jobs.")
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={"Apply": st.column_config.LinkColumn("Apply")},
    )
    st.download_button(
        "Download displayed results as CSV",
        data=_csv_bytes(rows),
        file_name="ranked_job_search_results.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download Excel results",
        data=_excel_bytes(rows),
        file_name="ranked_job_search_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def filter_matches(
    matches: list[MatchResult],
    query: str,
) -> list[MatchResult]:
    """Filter ranked rows without changing their score order."""

    terms = [term.casefold() for term in query.split() if term.strip()]
    if not terms:
        return list(matches)
    filtered: list[MatchResult] = []
    for match in matches:
        haystack = " ".join(
            [
                match.job.source,
                match.job.title,
                match.job.company,
                match.job.location or "",
                *match.matched_skills,
                *match.missing_skills,
                match.explanation,
            ]
        ).casefold()
        if all(term in haystack for term in terms):
            filtered.append(match)
    return filtered


def _match_row(match: MatchResult) -> dict[str, object]:
    job = match.job
    return {
        "Score": match.score,
        "Source": job.source,
        "Title": job.title,
        "Company": job.company,
        "Location": job.location or "",
        "Posted": job.posted_date.isoformat() if job.posted_date else "",
        "Workplace": job.workplace_type or "",
        "Matched skills": ", ".join(match.matched_skills),
        "Missing skills": ", ".join(match.missing_skills),
        "Why it matched": match.explanation,
        "Apply": str(job.apply_url),
    }


def _csv_bytes(rows: list[dict[str, object]]) -> bytes:
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


def _excel_bytes(rows: list[dict[str, object]]) -> bytes:
    output = BytesIO()
    pd.DataFrame(rows).to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()


def _load_streamlit() -> Any:
    import streamlit as st

    return st
