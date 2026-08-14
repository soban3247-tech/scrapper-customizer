"""Truthful CV tailoring and template rendering."""

from .comparison import CvEvidenceExcerpt, CvJobComparison, compare_cv_to_job
from .draft import (
    CvDraft,
    CvDraftItem,
    CvDraftSection,
    apply_cv_edits,
    create_cv_draft,
    render_cv_draft_text,
)
from .errors import CvCustomizationError, UnsupportedCvEditError

__all__ = [
    "CvCustomizationError",
    "CvDraft",
    "CvDraftItem",
    "CvDraftSection",
    "CvEvidenceExcerpt",
    "CvJobComparison",
    "UnsupportedCvEditError",
    "apply_cv_edits",
    "compare_cv_to_job",
    "create_cv_draft",
    "render_cv_draft_text",
]

