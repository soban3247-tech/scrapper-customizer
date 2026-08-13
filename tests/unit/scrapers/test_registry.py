import pytest

from job_assistant.models import Job, SearchConfig
from job_assistant.scrapers import (
    ScrapeResult,
    ScraperCapabilities,
    ScraperRegistrationError,
    ScraperRegistry,
    ScraperRequestError,
)


class SuccessfulScraper:
    capabilities = ScraperCapabilities()

    def __init__(self, source_id: str, display_name: str | None = None) -> None:
        self.source_id = source_id
        self.display_name = display_name or source_id.title()

    def search(self, config: SearchConfig) -> ScrapeResult:
        return ScrapeResult(
            source_id=self.source_id,
            jobs=[
                Job(
                    source=self.display_name,
                    title=f"{config.query} Developer",
                    company="Example Ltd",
                    apply_url=f"https://example.com/{self.source_id}/1",
                )
            ],
        )


class FailingScraper(SuccessfulScraper):
    def search(self, config: SearchConfig) -> ScrapeResult:
        raise ScraperRequestError("The platform timed out")


class UnexpectedFailingScraper(SuccessfulScraper):
    def search(self, config: SearchConfig) -> ScrapeResult:
        raise RuntimeError("private implementation detail")


class WrongResultScraper(SuccessfulScraper):
    def search(self, config: SearchConfig) -> ScrapeResult:
        return ScrapeResult(source_id="some-other-source")


class InvalidMetadataScraper(SuccessfulScraper):
    capabilities = "not capability metadata"


def test_registry_exposes_ui_metadata_and_case_insensitive_lookup() -> None:
    scraper = SuccessfulScraper("remote-ok", "Remote OK")
    registry = ScraperRegistry([scraper])

    assert registry.get("REMOTE-OK") is scraper
    assert registry.descriptors()[0].display_name == "Remote OK"


def test_registry_supports_runtime_switching_from_search_config() -> None:
    registry = ScraperRegistry(
        [SuccessfulScraper("alpha"), SuccessfulScraper("beta")]
    )
    config = SearchConfig(query="Python", sources=["beta"])

    results = registry.run_selected(config)

    assert [result.source_id for result in results] == ["beta"]
    assert results[0].jobs[0].title == "Python Developer"


def test_one_failure_does_not_stop_other_selected_scrapers() -> None:
    registry = ScraperRegistry(
        [
            FailingScraper("unavailable"),
            SuccessfulScraper("working"),
        ]
    )
    config = SearchConfig(query="Python", sources=["unavailable", "working"])

    failed, succeeded = registry.run_selected(config)

    assert failed.succeeded is False
    assert failed.issues[0].code == "request_error"
    assert failed.issues[0].retryable is True
    assert succeeded.succeeded is True
    assert len(succeeded.jobs) == 1


def test_unknown_future_source_is_reported_without_crashing_other_sources() -> None:
    registry = ScraperRegistry([SuccessfulScraper("working")])
    config = SearchConfig(query="Python", sources=["future-source", "working"])

    missing, succeeded = registry.run_selected(config)

    assert missing.succeeded is False
    assert missing.issues[0].code == "scraper_not_found"
    assert succeeded.succeeded is True


def test_unexpected_errors_are_isolated_without_leaking_details() -> None:
    registry = ScraperRegistry([UnexpectedFailingScraper("broken")])

    result = registry.run_selected(
        SearchConfig(query="Python", sources=["broken"])
    )[0]

    assert result.issues[0].code == "unexpected_error"
    assert "private implementation detail" not in result.issues[0].message


def test_adapter_cannot_return_a_result_for_another_source() -> None:
    registry = ScraperRegistry([WrongResultScraper("wrong")])

    result = registry.run_selected(
        SearchConfig(query="Python", sources=["wrong"])
    )[0]

    assert result.succeeded is False
    assert result.issues[0].code == "contract_error"


def test_registry_rejects_duplicate_source_ids_case_insensitively() -> None:
    registry = ScraperRegistry([SuccessfulScraper("remote-ok")])

    with pytest.raises(ScraperRegistrationError, match="already registered"):
        registry.register(SuccessfulScraper("REMOTE-OK"))


def test_registry_rejects_invalid_adapter_metadata_cleanly() -> None:
    with pytest.raises(ScraperRegistrationError, match="metadata"):
        ScraperRegistry([InvalidMetadataScraper("invalid")])
