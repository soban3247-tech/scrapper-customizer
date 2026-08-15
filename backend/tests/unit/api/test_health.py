from job_assistant.api.routes.health import health


def test_health_reports_ready_service() -> None:
    assert health() == {"status": "ok"}
