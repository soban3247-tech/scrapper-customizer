"""Reader-to-profile tests using version-controlled synthetic CV files."""

from pathlib import Path

from job_assistant.resume import ResumeFormat, extract_profile, read_resume

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "cvs"


def test_extracts_backend_profile_from_sample_pdf() -> None:
    document = read_resume(FIXTURE_DIR / "synthetic_backend_cv.pdf")
    profile = extract_profile(document.text)

    assert document.format is ResumeFormat.PDF
    assert document.page_count == 1
    assert profile.job_titles == ["Senior Backend Developer"]
    assert profile.years_experience == 6
    assert profile.skills == [
        "Python",
        "Django",
        "FastAPI",
        "REST APIs",
        "PostgreSQL",
        "Git",
        "Docker",
        "AWS",
    ]
    assert profile.education == [
        "BS Computer Science, Fictional State University, 2018"
    ]
    assert profile.domain == "Software Engineering"


def test_extracts_data_profile_from_sample_docx() -> None:
    document = read_resume(FIXTURE_DIR / "synthetic_data_cv.docx")
    profile = extract_profile(document.text)

    assert document.format is ResumeFormat.DOCX
    assert document.page_count is None
    assert profile.job_titles == ["Data Analyst"]
    assert profile.years_experience == 3
    assert profile.skills == [
        "Python",
        "SQL",
        "Power BI",
        "Tableau",
        "Excel",
    ]
    assert profile.education == [
        "Master of Data Science, Fictional State University, 2022"
    ]
    assert profile.domain == "Data and AI"
