from pathlib import Path

from job_assistant.api.main import configured_frontend_origins, load_environment
from job_assistant.api.routes.health import health


def test_health_reports_ready_service() -> None:
    assert health() == {"status": "ok"}


def test_root_env_loader_supports_documented_frontend_origins(
    tmp_path: Path, monkeypatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FRONTEND_ORIGINS=https://app.example.com,https://admin.example.com\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FRONTEND_ORIGINS", raising=False)

    load_environment(env_file)

    assert configured_frontend_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]
