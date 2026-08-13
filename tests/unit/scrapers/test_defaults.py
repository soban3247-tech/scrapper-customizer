from job_assistant.models import JobSource
from job_assistant.scrapers import create_default_registry


def test_default_registry_contains_all_seven_mvp_sources() -> None:
    registry = create_default_registry()

    assert {descriptor.source_id for descriptor in registry.descriptors()} == {
        JobSource.HIRINGCAFE.value,
        JobSource.REMOTIVE.value,
        JobSource.ARBEITNOW.value,
        JobSource.REMOTE_OK.value,
        JobSource.GREENHOUSE.value,
        JobSource.LEVER.value,
        JobSource.ASHBY.value,
    }
