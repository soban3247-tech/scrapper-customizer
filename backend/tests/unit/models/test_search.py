import pytest
from pydantic import ValidationError

from job_assistant.models import JobSource, SearchConfig


def test_search_config_has_safe_default_sources() -> None:
    config = SearchConfig(query=" Python developer ")

    assert config.query == "Python developer"
    assert config.sources == [
        JobSource.HIRINGCAFE,
        JobSource.REMOTIVE,
        JobSource.ARBEITNOW,
        JobSource.REMOTE_OK,
    ]


def test_search_config_cleans_lists_and_duplicate_sources() -> None:
    config = SearchConfig(
        query="developer",
        skills=["Python", " python ", "SQL"],
        sources=[JobSource.REMOTIVE, JobSource.REMOTIVE],
    )

    assert config.skills == ["Python", "SQL"]
    assert config.sources == [JobSource.REMOTIVE]


def test_search_config_accepts_future_source_and_generic_options() -> None:
    config = SearchConfig(
        query="developer",
        sources=["future-board"],
        source_options={
            "Future-Board": {"tenant": "example", "include_contracts": True}
        },
    )

    assert config.sources == ["future-board"]
    assert config.options_for("future-board") == {
        "tenant": "example",
        "include_contracts": True,
    }


def test_board_source_requires_at_least_one_board_name() -> None:
    with pytest.raises(ValidationError, match="greenhouse_boards"):
        SearchConfig(query="developer", sources=[JobSource.GREENHOUSE])


def test_board_source_accepts_board_names() -> None:
    config = SearchConfig(
        query="developer",
        sources=[JobSource.GREENHOUSE],
        greenhouse_boards=["openai"],
    )

    assert config.greenhouse_boards == ["openai"]


@pytest.mark.parametrize(
    ("source", "option_key"),
    [
        (JobSource.GREENHOUSE, "boards"),
        (JobSource.LEVER, "companies"),
        (JobSource.ASHBY, "organizations"),
    ],
)
def test_board_source_accepts_generic_ui_configuration(
    source: JobSource, option_key: str
) -> None:
    config = SearchConfig(
        query="developer",
        sources=[source],
        source_options={source.value: {option_key: ["example"]}},
    )

    assert config.options_for(source.value)[option_key] == ["example"]


@pytest.mark.parametrize("max_pages", [0, 26])
def test_search_config_rejects_unsafe_page_limits(max_pages: int) -> None:
    with pytest.raises(ValidationError):
        SearchConfig(query="developer", max_pages=max_pages)


def test_search_config_requires_a_source() -> None:
    with pytest.raises(ValidationError):
        SearchConfig(query="developer", sources=[])

