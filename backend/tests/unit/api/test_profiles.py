import asyncio
from pathlib import Path
from threading import get_ident

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from job_assistant.api.main import app
from job_assistant.api.routes import profiles as profiles_route
from job_assistant.resume import DEFAULT_MAX_FILE_SIZE

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


class RecordingUpload:
    def __init__(self, data: bytes, *, size: int | None) -> None:
        self.filename = "resume.pdf"
        self.size = size
        self.data = data
        self.read_sizes: list[int] = []
        self.closed = False

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self.data[:size]

    async def close(self) -> None:
        self.closed = True


def test_rejects_known_oversized_upload_before_reading_it() -> None:
    upload = RecordingUpload(b"not read", size=DEFAULT_MAX_FILE_SIZE + 1)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(profiles_route.extract_cv_profile(upload))  # type: ignore[arg-type]

    assert exc_info.value.status_code == 413
    assert upload.read_sizes == []
    assert upload.closed is True


def test_unknown_upload_size_is_read_with_a_strict_bound() -> None:
    upload = RecordingUpload(
        b"x" * (DEFAULT_MAX_FILE_SIZE + 1),
        size=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(profiles_route.extract_cv_profile(upload))  # type: ignore[arg-type]

    assert exc_info.value.status_code == 413
    assert upload.read_sizes == [DEFAULT_MAX_FILE_SIZE + 1]


def test_document_parsing_runs_outside_the_event_loop_thread(monkeypatch) -> None:
    upload = RecordingUpload(b"small upload", size=12)
    parser_thread: list[int] = []
    event_loop_thread: list[int] = []

    def recording_parser(data: bytes, filename: str):
        parser_thread.append(get_ident())
        raise ValueError("synthetic parser stop")

    monkeypatch.setattr(profiles_route, "_parse_and_extract", recording_parser)

    async def invoke() -> None:
        event_loop_thread.append(get_ident())
        with pytest.raises(HTTPException):
            await profiles_route.extract_cv_profile(upload)  # type: ignore[arg-type]

    asyncio.run(invoke())

    assert parser_thread
    assert parser_thread[0] != event_loop_thread[0]
