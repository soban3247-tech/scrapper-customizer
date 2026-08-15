from pathlib import Path

from fastapi.testclient import TestClient

from job_assistant.api.main import app

FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "cvs"
client = TestClient(app)


def test_extract_profile_from_docx() -> None:
    cv_path = FIXTURE_DIR / "synthetic_data_cv.docx"

    with cv_path.open("rb") as cv_file:
        response = client.post(
            "/profiles/extract",
            files={
                "file": (
                    cv_path.name,
                    cv_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["filename"] == cv_path.name
    assert "Python" in payload["profile"]["skills"]
    assert payload["suggested_search"]["query"]
    assert payload["suggested_search"]["skills"]


def test_rejects_unsupported_resume_type() -> None:
    response = client.post(
        "/profiles/extract",
        files={"file": ("resume.txt", b"Python developer", "text/plain")},
    )

    assert response.status_code == 422
    assert "PDF and DOCX" in response.json()["detail"]
