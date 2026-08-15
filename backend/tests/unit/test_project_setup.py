"""Smoke tests for the Phase 0 package scaffold."""


def test_core_package_is_importable() -> None:
    import job_assistant

    assert job_assistant.__doc__
