from datetime import date
from pathlib import Path

from job_assistant.models import Job, MatchResult, SearchConfig
from job_assistant.storage import SearchResultRepository


def match(score: float, url_id: str) -> MatchResult:
    return MatchResult(
        job=Job(
            source="Example",
            title="Python Developer",
            company="Example Ltd",
            posted_date=date(2026, 8, 12),
            apply_url=f"https://example.com/jobs/{url_id}",
        ),
        score=score,
        matched_skills=["Python"],
        explanation="Matched Python.",
    )


def test_saves_and_loads_normalized_jobs_with_match_details(tmp_path: Path) -> None:
    repository = SearchResultRepository(tmp_path / "results.db")
    config = SearchConfig(query="Python", sources=["Example"])
    matches = [match(90, "one"), match(70, "two")]

    search_id = repository.save(config, matches)

    assert repository.load(search_id) == matches
    assert repository.load_latest() == (search_id, matches)


def test_does_not_store_source_credentials(tmp_path: Path) -> None:
    database_path = tmp_path / "safe-results.db"
    repository = SearchResultRepository(database_path)
    config = SearchConfig(
        query="Python",
        sources=["Private Source"],
        source_options={"Private Source": {"api_key": "super-secret-value"}},
    )

    repository.save(config, [match(80, "safe")])

    assert b"super-secret-value" not in database_path.read_bytes()


def test_empty_search_is_saved_as_a_valid_run(tmp_path: Path) -> None:
    repository = SearchResultRepository(tmp_path / "empty.db")

    search_id = repository.save(
        SearchConfig(query="Rare Role", sources=["Example"]),
        [],
    )

    assert repository.load(search_id) == []
