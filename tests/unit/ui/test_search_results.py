from datetime import date
import csv
from io import BytesIO, StringIO

from openpyxl import load_workbook

from job_assistant.models import Job, MatchResult
from ui.search_results import _csv_bytes, _excel_bytes, _match_row, filter_matches


def result() -> MatchResult:
    return MatchResult(
        score=88,
        matched_skills=["Python", "SQL"],
        missing_skills=["Docker"],
        explanation="Strong title and skill alignment.",
        job=Job(
        source="Remotive",
        title="Python Developer",
        company="Example Ltd",
        location="Remote",
        posted_date=date(2026, 8, 12),
        apply_url="https://example.com/jobs/1",
        ),
    )


def test_excel_download_contains_ranked_job_fields() -> None:
    workbook = load_workbook(filename=BytesIO(_excel_bytes([_match_row(result())])))
    sheet = workbook.active

    assert sheet["A2"].value == 88
    assert sheet["B2"].value == "Remotive"
    assert sheet["C2"].value == "Python Developer"
    assert sheet["K2"].value == "https://example.com/jobs/1"


def test_csv_download_contains_only_displayed_rows() -> None:
    rows = [_match_row(result())]

    content = _csv_bytes(rows).decode("utf-8-sig")
    parsed = list(csv.DictReader(StringIO(content)))

    assert len(parsed) == 1
    assert parsed[0]["Score"] == "88.0"
    assert parsed[0]["Apply"] == "https://example.com/jobs/1"


def test_table_filter_searches_company_location_and_skills() -> None:
    match = result()

    assert filter_matches([match], "example python") == [match]
    assert filter_matches([match], "karachi") == []
