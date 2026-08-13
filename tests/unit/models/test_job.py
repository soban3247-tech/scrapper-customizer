from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from job_assistant.models import Job


def make_job(**overrides: object) -> Job:
    values: dict[str, object] = {
        "source": "Remotive",
        "source_job_id": "job-123",
        "title": "Python Developer",
        "company": "Example Ltd",
        "apply_url": "https://example.com/jobs/123",
    }
    values.update(overrides)
    return Job(**values)


def test_job_accepts_normalized_scraper_data() -> None:
    job = make_job(
        posted_date="2026-08-12",
        salary_min="70000",
        salary_max="90000",
        salary_currency="USD",
        tags=["Python", "Remote"],
    )

    assert job.posted_date == date(2026, 8, 12)
    assert job.salary_min == Decimal("70000")
    assert str(job.apply_url) == "https://example.com/jobs/123"


@pytest.mark.parametrize("field", ["source", "title", "company"])
def test_job_rejects_blank_required_text(field: str) -> None:
    with pytest.raises(ValidationError):
        make_job(**{field: "   "})


def test_job_rejects_invalid_apply_url() -> None:
    with pytest.raises(ValidationError):
        make_job(apply_url="not-a-url")


def test_job_rejects_reversed_salary_range() -> None:
    with pytest.raises(ValidationError, match="salary_max"):
        make_job(salary_min=90000, salary_max=70000)


def test_job_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        make_job(unexpected="value")

