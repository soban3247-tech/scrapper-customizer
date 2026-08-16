from datetime import date

from fastapi.testclient import TestClient

from job_assistant.api.main import app
from job_assistant.api.routes.jobs import get_scraper_registry
from job_assistant.models import Job, SearchConfig
from job_assistant.scrapers import ScrapeResult, ScraperCapabilities, ScraperRegistry


class FakeScraper:
    source_id = "Fixture"
    display_name = "Fixture Jobs"
    capabilities = ScraperCapabilities(supports_posted_after=True)

    def search(self, config: SearchConfig) -> ScrapeResult:
        return ScrapeResult(
            source_id=self.source_id,
            jobs=[
                Job(
                    source=self.source_id,
                    source_job_id="fixture-1",
                    title=config.query,
                    company="Example Co",
                    posted_date=date(2026, 8, 10),
                    apply_url="https://example.com/jobs/fixture-1",
                    tags=config.skills,
                )
            ],
        )


class PreferenceScraper:
    source_id = "Preferences"
    display_name = "Preference Fixtures"
    capabilities = ScraperCapabilities()

    def search(self, config: SearchConfig) -> ScrapeResult:
        return ScrapeResult(
            source_id=self.source_id,
            jobs=[
                Job(
                    source=self.source_id,
                    source_job_id="karachi-onsite",
                    title="Backend Engineer",
                    company="Example Co",
                    location="Karachi, Pakistan",
                    workplace_type="On-site",
                    apply_url="https://example.com/jobs/karachi-onsite",
                ),
                Job(
                    source=self.source_id,
                    source_job_id="karachi-remote",
                    title="Backend Engineer",
                    company="Example Co",
                    location="Karachi, Pakistan",
                    workplace_type="Remote",
                    apply_url="https://example.com/jobs/karachi-remote",
                ),
                Job(
                    source=self.source_id,
                    source_job_id="lahore-remote",
                    title="Backend Engineer",
                    company="Example Co",
                    location="Lahore, Pakistan",
                    workplace_type="Remote",
                    apply_url="https://example.com/jobs/lahore-remote",
                ),
            ],
        )


def _fake_registry() -> ScraperRegistry:
    return ScraperRegistry([FakeScraper()])


def _preference_registry() -> ScraperRegistry:
    return ScraperRegistry([PreferenceScraper()])


def test_lists_registered_sources() -> None:
    app.dependency_overrides[get_scraper_registry] = _fake_registry
    try:
        response = TestClient(app).get("/jobs/sources")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["source_id"] == "Fixture"


def test_searches_with_normalized_config() -> None:
    app.dependency_overrides[get_scraper_registry] = _fake_registry
    try:
        response = TestClient(app).post(
            "/jobs/search",
            json={
                "query": "Backend Engineer",
                "skills": ["Python", "FastAPI"],
                "sources": ["Fixture"],
                "posted_after": "2026-08-01",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"][0]["title"] == "Backend Engineer"
    assert payload["jobs"][0]["tags"] == ["Python", "FastAPI"]


def test_search_applies_location_and_remote_only_filters_together() -> None:
    app.dependency_overrides[get_scraper_registry] = _preference_registry
    try:
        response = TestClient(app).post(
            "/jobs/search",
            json={
                "query": "Backend Engineer",
                "sources": ["Preferences"],
                "location": "  KARACHI  ",
                "remote_only": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    jobs = response.json()["jobs"]
    assert [job["source_job_id"] for job in jobs] == ["karachi-remote"]
