"""Streamlit progress and raw results for a multi-source job search."""

from io import BytesIO
from typing import Any

import pandas as pd

from job_assistant.models import Job, SearchConfig
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
    """Display source outcomes, errors, raw jobs, and the legacy Excel export."""

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

    rows = [_job_row(job) for job in result.jobs]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.download_button(
        "Download Excel results",
        data=_excel_bytes(rows),
        file_name="job_search_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _job_row(job: Job) -> dict[str, object]:
    return {
        "Source": job.source,
        "Title": job.title,
        "Company": job.company,
        "Location": job.location or "",
        "Posted": job.posted_date.isoformat() if job.posted_date else "",
        "Workplace": job.workplace_type or "",
        "Apply": str(job.apply_url),
    }


def _excel_bytes(rows: list[dict[str, object]]) -> bytes:
    output = BytesIO()
    pd.DataFrame(rows).to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()


def _load_streamlit() -> Any:
    import streamlit as st

    return st
