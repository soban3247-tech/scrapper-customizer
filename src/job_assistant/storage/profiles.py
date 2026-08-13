"""SQLite persistence for confirmed user profiles."""

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from job_assistant.models import Profile

from .errors import ProfileStorageError

DEFAULT_DATABASE_PATH = Path("data/job_assistant.db")
DEFAULT_PROFILE_KEY = "default"

_CREATE_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS profiles (
    profile_key TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_UPSERT_PROFILE = """
INSERT INTO profiles (profile_key, profile_json, updated_at)
VALUES (?, ?, ?)
ON CONFLICT(profile_key) DO UPDATE SET
    profile_json = excluded.profile_json,
    updated_at = excluded.updated_at
"""


class ProfileRepository:
    """Save and retrieve validated profiles from one local SQLite database."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        configured_path = database_path or os.getenv(
            "DATABASE_PATH",
            str(DEFAULT_DATABASE_PATH),
        )
        self.database_path = Path(configured_path)
        self._prepare_database()

    def save(
        self,
        profile: Profile,
        *,
        profile_key: str = DEFAULT_PROFILE_KEY,
    ) -> None:
        """Insert or replace a confirmed profile under a stable local key."""

        key = _validate_profile_key(profile_key)
        if not isinstance(profile, Profile):
            raise TypeError("profile must be a Profile")

        timestamp = datetime.now(UTC).isoformat()
        try:
            with self._connect() as connection:
                connection.execute(
                    _UPSERT_PROFILE,
                    (key, profile.model_dump_json(), timestamp),
                )
        except sqlite3.Error as exc:
            raise ProfileStorageError("The profile could not be saved") from exc

    def load(
        self,
        *,
        profile_key: str = DEFAULT_PROFILE_KEY,
    ) -> Profile | None:
        """Return a saved profile, or None when the key has not been saved."""

        key = _validate_profile_key(profile_key)
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT profile_json FROM profiles WHERE profile_key = ?",
                    (key,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise ProfileStorageError("The profile could not be loaded") from exc

        if row is None:
            return None
        try:
            return Profile.model_validate_json(row["profile_json"])
        except (ValidationError, ValueError, TypeError) as exc:
            raise ProfileStorageError(
                "The saved profile is invalid and could not be loaded"
            ) from exc

    def delete(
        self,
        *,
        profile_key: str = DEFAULT_PROFILE_KEY,
    ) -> bool:
        """Delete a saved profile and report whether one existed."""

        key = _validate_profile_key(profile_key)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM profiles WHERE profile_key = ?",
                    (key,),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            raise ProfileStorageError("The profile could not be deleted") from exc

    def _prepare_database(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(_CREATE_PROFILES_TABLE)
        except (OSError, sqlite3.Error) as exc:
            raise ProfileStorageError(
                "The profile database could not be opened"
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection


def _validate_profile_key(profile_key: str) -> str:
    if not isinstance(profile_key, str):
        raise TypeError("profile_key must be a string")
    key = profile_key.strip()
    if not key:
        raise ValueError("profile_key must not be empty")
    if len(key) > 100:
        raise ValueError("profile_key must not exceed 100 characters")
    return key
