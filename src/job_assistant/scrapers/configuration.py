"""Helpers for resolving adapter-specific settings from search configuration."""

from collections.abc import Sequence

from job_assistant.models import SearchConfig

from .errors import ScraperConfigurationError
from .parsing import string_list


def configured_targets(
    config: SearchConfig,
    *,
    source_id: str,
    option_key: str,
    legacy_values: Sequence[str],
    target_label: str,
) -> list[str]:
    """Resolve target names from legacy fields or generic UI source options."""

    targets = string_list(list(legacy_values))
    if not targets:
        targets = string_list(config.options_for(source_id).get(option_key))
    if not targets:
        raise ScraperConfigurationError(
            f"At least one {target_label} is required for {source_id}"
        )
    return targets
