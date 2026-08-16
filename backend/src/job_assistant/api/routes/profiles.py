"""CV upload and profile extraction routes."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from job_assistant.models import Profile
from job_assistant.models.search import DEFAULT_SOURCES
from job_assistant.resume import (
    DEFAULT_MAX_FILE_SIZE,
    ProfileExtraction,
    ResumeDocument,
    ResumeFileTooLargeError,
    ResumeReadError,
    extract_profile_with_evidence,
    read_resume_bytes,
)

from ..schemas import (
    ExtractionEvidenceResponse,
    ProfileExtractionResponse,
    ResumeMetadata,
    SuggestedSearch,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _upload_too_large() -> ResumeFileTooLargeError:
    limit_mb = DEFAULT_MAX_FILE_SIZE // (1024 * 1024)
    return ResumeFileTooLargeError(
        f"The uploaded CV exceeds the {limit_mb} MB size limit"
    )


async def _read_bounded_upload(file: UploadFile) -> bytes:
    """Read no more than the configured limit plus one sentinel byte."""
    if file.size is not None and file.size > DEFAULT_MAX_FILE_SIZE:
        raise _upload_too_large()

    data = await file.read(DEFAULT_MAX_FILE_SIZE + 1)
    if len(data) > DEFAULT_MAX_FILE_SIZE:
        raise _upload_too_large()
    return data


def _parse_and_extract(
    data: bytes, filename: str
) -> tuple[ResumeDocument, ProfileExtraction]:
    document = read_resume_bytes(data, filename)
    extraction = extract_profile_with_evidence(document.text)
    return document, extraction


@router.post("/extract", response_model=ProfileExtractionResponse)
async def extract_cv_profile(
    file: UploadFile = File(..., description="A PDF or DOCX CV, up to 10 MB"),
) -> ProfileExtractionResponse:
    filename = file.filename or "resume"
    try:
        data = await _read_bounded_upload(file)
        document, extraction = await run_in_threadpool(
            _parse_and_extract, data, filename
        )
    except ResumeFileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except (ResumeReadError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()

    return ProfileExtractionResponse(
        document=ResumeMetadata(
            filename=document.filename,
            format=document.format.value,
            page_count=document.page_count,
        ),
        profile=extraction.profile,
        evidence=ExtractionEvidenceResponse(
            skill_matches={
                skill: list(matches)
                for skill, matches in extraction.evidence.skill_matches.items()
            },
            title_matches={
                title: list(matches)
                for title, matches in extraction.evidence.title_matches.items()
            },
            experience_phrases=list(extraction.evidence.experience_phrases),
            education_lines=list(extraction.evidence.education_lines),
            domain_scores=dict(extraction.evidence.domain_scores),
        ),
        suggested_search=_suggest_search(extraction.profile),
    )


def _suggest_search(profile: Profile) -> SuggestedSearch:
    query = next(
        (
            value
            for value in (
                profile.job_titles[0] if profile.job_titles else None,
                profile.domain,
                profile.skills[0] if profile.skills else None,
            )
            if value
        ),
        "",
    )
    return SuggestedSearch(
        query=query,
        skills=profile.skills,
        location=(
            profile.preferred_locations[0] if profile.preferred_locations else None
        ),
        remote_only=profile.remote_preference is True,
        sources=list(DEFAULT_SOURCES),
    )
