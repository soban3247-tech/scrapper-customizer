"""SQLite persistence for ranked job-search results."""

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from job_assistant.models import MatchResult, SearchConfig

from .errors import SearchResultStorageError
from .profiles import DEFAULT_DATABASE_PATH

_CREATE_SEARCH_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS search_runs (
    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_CREATE_JOB_MATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS job_matches (
    search_id INTEGER NOT NULL,
    result_rank INTEGER NOT NULL,
    match_json TEXT NOT NULL,
    PRIMARY KEY (search_id, result_rank),
    FOREIGN KEY (search_id) REFERENCES search_runs(search_id) ON DELETE CASCADE
)
"""


class SearchResultRepository:
    """Store normalized jobs and their explainable match details together."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        configured_path = database_path or os.getenv(
            "DATABASE_PATH",
            str(DEFAULT_DATABASE_PATH),
        )
        self.database_path = Path(configured_path)
        self._prepare_database()

    def save(self, config: SearchConfig, matches: list[MatchResult]) -> int:
        """Persist one ranked search without storing source credentials."""

        if not isinstance(config, SearchConfig):
            raise TypeError("config must be a SearchConfig")
        if not isinstance(matches, list) or not all(
            isinstance(match, MatchResult) for match in matches
        ):
            raise TypeError("matches must be a list of MatchResult values")

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO search_runs (query, sources_json, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        config.query,
                        json.dumps(config.sources),
                        datetime.now(UTC).isoformat(),
                    ),
                )
                search_id = int(cursor.lastrowid)
                connection.executemany(
                    """
                    INSERT INTO job_matches (search_id, result_rank, match_json)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (search_id, rank, match.model_dump_json())
                        for rank, match in enumerate(matches, start=1)
                    ],
                )
        except sqlite3.Error as exc:
            raise SearchResultStorageError(
                "The ranked search results could not be saved"
            ) from exc
        return search_id

    def load(self, search_id: int) -> list[MatchResult]:
        """Load ranked results in their original score order."""

        if not isinstance(search_id, int) or isinstance(search_id, bool):
            raise TypeError("search_id must be an integer")
        if search_id < 1:
            raise ValueError("search_id must be at least 1")
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT match_json FROM job_matches
                    WHERE search_id = ?
                    ORDER BY result_rank
                    """,
                    (search_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise SearchResultStorageError(
                "The ranked search results could not be loaded"
            ) from exc
        try:
            return [MatchResult.model_validate_json(row["match_json"]) for row in rows]
        except (ValidationError, ValueError, TypeError) as exc:
            raise SearchResultStorageError(
                "The saved ranked results are invalid and could not be loaded"
            ) from exc

    def load_latest(self) -> tuple[int, list[MatchResult]] | None:
        """Return the most recently saved search, when one exists."""

        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT search_id FROM search_runs ORDER BY search_id DESC LIMIT 1"
                ).fetchone()
        except sqlite3.Error as exc:
            raise SearchResultStorageError(
                "The latest ranked search could not be loaded"
            ) from exc
        if row is None:
            return None
        search_id = int(row["search_id"])
        return search_id, self.load(search_id)

    def _prepare_database(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(_CREATE_SEARCH_RUNS_TABLE)
                connection.execute(_CREATE_JOB_MATCHES_TABLE)
        except (OSError, sqlite3.Error) as exc:
            raise SearchResultStorageError(
                "The search-results database could not be opened"
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
