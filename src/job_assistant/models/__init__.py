"""Shared validated data models used across application modules."""

from .job import Job
from .match import MatchResult
from .profile import Profile
from .search import JobSource, SearchConfig

__all__ = ["Job", "JobSource", "MatchResult", "Profile", "SearchConfig"]

