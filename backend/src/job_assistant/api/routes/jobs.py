"""Source discovery and normalized multi-source job search routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from job_assistant.models import SearchConfig
from job_assistant.scrapers import (
    ScraperDescriptor,
    ScraperRegistry,
    collect_jobs,
    create_default_registry,
    filter_jobs_by_date,
)

from ..schemas import JobSearchResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_scraper_registry() -> ScraperRegistry:
    return create_default_registry()


RegistryDependency = Annotated[ScraperRegistry, Depends(get_scraper_registry)]


@router.get("/sources", response_model=list[ScraperDescriptor])
def list_sources(registry: RegistryDependency) -> list[ScraperDescriptor]:
    return registry.descriptors()


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(
    config: SearchConfig,
    registry: RegistryDependency,
) -> JobSearchResponse:
    jobs, issues = await run_in_threadpool(collect_jobs, registry, config)
    missing_date_count = 0
    if config.posted_after is not None:
        jobs, missing_date_count = filter_jobs_by_date(jobs, config.posted_after)
    return JobSearchResponse(
        jobs=jobs,
        issues=issues,
        missing_date_count=missing_date_count,
    )
