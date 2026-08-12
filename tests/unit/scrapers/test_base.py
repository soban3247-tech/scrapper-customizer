from job_assistant.models import Job, SearchConfig
from job_assistant.scrapers import (
    ConfigFieldKind,
    JobScraper,
    ScrapeResult,
    ScraperCapabilities,
    ScraperConfigField,
    ScraperIssue,
)


class MetadataScraper:
    source_id = "future-board"
    display_name = "Future Board"
    capabilities = ScraperCapabilities(
        supports_pagination=True,
        requires_credentials=True,
        configuration_fields=(
            ScraperConfigField(
                key="api_token",
                label="API token",
                kind=ConfigFieldKind.SECRET,
                required=True,
            ),
        ),
    )

    def search(self, config: SearchConfig) -> ScrapeResult:
        return ScrapeResult(source_id=self.source_id)


def test_adapter_satisfies_runtime_protocol() -> None:
    assert isinstance(MetadataScraper(), JobScraper)


def test_capability_metadata_can_drive_dynamic_ui_controls() -> None:
    capabilities = MetadataScraper.capabilities

    assert capabilities.supports_pagination is True
    assert capabilities.requires_credentials is True
    assert capabilities.configuration_fields[0].key == "api_token"
    assert capabilities.configuration_fields[0].kind is ConfigFieldKind.SECRET


def test_result_can_contain_jobs_and_nonfatal_issues() -> None:
    job = Job(
        source="Future Board",
        title="Python Developer",
        company="Example Ltd",
        apply_url="https://example.com/jobs/1",
    )
    result = ScrapeResult(
        source_id="future-board",
        jobs=[job],
        issues=[
            ScraperIssue(
                source_id="future-board",
                code="page_unavailable",
                message="Page 2 could not be loaded; page 1 results were retained.",
                retryable=True,
            )
        ],
    )

    assert result.jobs == [job]
    assert result.succeeded is True
    assert result.issues[0].fatal is False


def test_failure_result_is_structured_and_fatal() -> None:
    result = ScrapeResult.failure(
        "future-board",
        "The source timed out.",
        code="request_error",
        retryable=True,
    )

    assert result.jobs == []
    assert result.succeeded is False
    assert result.issues[0].retryable is True

