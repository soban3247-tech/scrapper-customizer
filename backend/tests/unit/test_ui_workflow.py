from datetime import date
from pathlib import Path

import UI
from job_assistant.models import Job
from job_assistant.scrapers import ScrapeResult, ScraperIssue


class FakeRegistry:
    def __init__(self, results: list[ScrapeResult]) -> None:
        self.results = results
        self.config = None

    def run_selected(self, config):
        self.config = config
        return self.results


def test_split_board_names_supports_all_ui_separators() -> None:
    assert UI.split_board_names("one,two;three\nfour/") == [
        "one",
        "two",
        "three",
        "four",
    ]


def test_ui_workflow_routes_sources_through_registry_and_exports(
    monkeypatch,
    tmp_path: Path,
) -> None:
    kept_job = Job(
        source="Remotive",
        title="Python Developer",
        company="Example Ltd",
        posted_date=date(2026, 8, 12),
        apply_url="https://example.com/jobs/1",
    )
    registry = FakeRegistry(
        [
            ScrapeResult(
                source_id="Remotive",
                jobs=[kept_job],
                issues=[
                    ScraperIssue(
                        source_id="Remotive",
                        message="One record was invalid",
                        code="invalid_job",
                    )
                ],
            )
        ]
    )
    monkeypatch.setattr(UI, "create_default_registry", lambda: registry)
    exported: dict[str, object] = {}

    def fake_export(jobs: list[Job], filename: str | Path) -> Path:
        exported["jobs"] = jobs
        exported["filename"] = filename
        return Path(filename).resolve()

    monkeypatch.setattr(UI, "export_to_excel", fake_export)
    logs: list[str] = []
    output = tmp_path / "jobs.xlsx"

    result = UI.run_scraper_workflow(
        query="Python",
        start_date=date(2026, 8, 1),
        max_pages=2,
        output_filename=output,
        selected_sources={"remotive": True, "ashby": False},
        greenhouse_boards=[],
        lever_companies=[],
        ashby_organizations=[],
        log=logs.append,
    )

    assert result == output.resolve()
    assert registry.config.sources == ["Remotive"]
    assert registry.config.max_pages == 2
    assert exported["jobs"] == [kept_job]
    assert any("warning" in message for message in logs)
