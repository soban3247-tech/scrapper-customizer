"""CV upload and profile extraction routes."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from job_assistant.models import Profile
from job_assistant.models.search import DEFAULT_SOURCES
from job_assistant.resume import (
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


@router.post("/extract", response_model=ProfileExtractionResponse)
async def extract_cv_profile(
    file: UploadFile = File(..., description="A PDF or DOCX CV, up to 10 MB"),
) -> ProfileExtractionResponse:
    filename = file.filename or "resume"
    try:
        document = read_resume_bytes(await file.read(), filename)
        extraction = extract_profile_with_evidence(document.text)
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
