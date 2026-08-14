from datetime import date

from openpyxl import load_workbook

from job_assistant.models import Job
from ui.search_results import _excel_bytes, _job_row


def test_excel_download_contains_normalized_job_fields() -> None:
    job = Job(
        source="Remotive",
        title="Python Developer",
        company="Example Ltd",
        location="Remote",
        posted_date=date(2026, 8, 12),
        apply_url="https://example.com/jobs/1",
    )

    workbook = load_workbook(filename=_bytes_file(_excel_bytes([_job_row(job)])))
    sheet = workbook.active

    assert sheet["A2"].value == "Remotive"
    assert sheet["B2"].value == "Python Developer"
    assert sheet["G2"].value == "https://example.com/jobs/1"


def _bytes_file(value: bytes):
    from io import BytesIO

    return BytesIO(value)
