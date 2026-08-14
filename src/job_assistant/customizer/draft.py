"""Evidence-locked CV reordering, safe wording, and editable draft validation."""

import hashlib
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from job_assistant.resume.taxonomy import SKILL_ALIASES

from .comparison import CvJobComparison
from .errors import UnsupportedCvEditError

_CONNECTOR_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "the",
    "to",
    "using",
    "with",
}

_PROTECTED_QUALIFIERS = {
    "basic",
    "beginner",
    "familiar",
    "familiarity",
    "junior",
    "learning",
    "limited",
    "no",
    "not",
    "novice",
    "supervised",
    "supervision",
    "under",
    "without",
}

_RESPONSIBILITY_REWRITES = {
    "building": "Built",
    "creating": "Created",
    "delivering": "Delivered",
    "designing": "Designed",
    "developing": "Developed",
    "implementing": "Implemented",
    "maintaining": "Maintained",
    "managing": "Managed",
    "supporting": "Supported",
}


class CvDraftItem(BaseModel):
    """One editable line tied to immutable original-CV evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    item_id: str = Field(pattern=r"^line-\d{4}$")
    original_text: str = Field(min_length=1)
    draft_text: str = Field(min_length=1)
    relevant: bool = False
    evidence_terms: list[str] = Field(default_factory=list)

    @field_validator("evidence_terms")
    @classmethod
    def clean_terms(cls, values: list[str]) -> list[str]:
        return _unique(values)


class CvDraftSection(BaseModel):
    """A preview section whose items retain their source identities."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    title: str = Field(min_length=1)
    items: list[CvDraftItem] = Field(min_length=1)


class CvDraft(BaseModel):
    """Reordered CV preview that can be validated after user edits."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    draft_id: str = Field(pattern=r"^[a-f0-9]{16}$")
    job_title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    sections: list[CvDraftSection] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("warnings")
    @classmethod
    def clean_warnings(cls, values: list[str]) -> list[str]:
        return _unique(values)

    @model_validator(mode="after")
    def require_unique_item_ids(self) -> "CvDraft":
        item_ids = [item.item_id for section in self.sections for item in section.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("CV draft item IDs must be unique")
        return self

    @property
    def items(self) -> list[CvDraftItem]:
        return [item for section in self.sections for item in section.items]


def create_cv_draft(
    comparison: CvJobComparison,
    original_cv_text: str,
) -> CvDraft:
    """Promote relevant source lines and apply conservative wording rules."""

    if not isinstance(comparison, CvJobComparison):
        raise TypeError("comparison must be a CvJobComparison")
    if not isinstance(original_cv_text, str):
        raise TypeError("original_cv_text must be a string")
    source_lines = _source_lines(original_cv_text)
    if not source_lines:
        raise ValueError("original CV text is required to create a draft")

    evidence_by_line = {
        excerpt.text.casefold(): excerpt.matched_terms
        for excerpt in comparison.relevant_cv_excerpts
    }
    relevant_items: list[CvDraftItem] = []
    other_items: list[CvDraftItem] = []
    for index, line in enumerate(source_lines, start=1):
        evidence_terms = evidence_by_line.get(line.casefold(), [])
        relevant = bool(evidence_terms)
        item = CvDraftItem(
            item_id=f"line-{index:04d}",
            original_text=line,
            draft_text=_safe_reword(line) if relevant else line,
            relevant=relevant,
            evidence_terms=evidence_terms,
        )
        (relevant_items if relevant else other_items).append(item)

    sections: list[CvDraftSection] = []
    if relevant_items:
        sections.append(
            CvDraftSection(title="Job-relevant CV content", items=relevant_items)
        )
    if other_items:
        sections.append(CvDraftSection(title="Other original CV content", items=other_items))

    job = comparison.match.job
    digest_input = f"{job.apply_url}\n" + "\n".join(source_lines)
    warnings = [
        *(f"Missing CV skill: {skill}" for skill in comparison.missing_skills),
    ]
    if comparison.required_years_experience is not None and not (
        comparison.experience_requirement_met
    ):
        warnings.append(
            f"Experience requirement is not supported: "
            f"{comparison.required_years_experience:g}+ years requested"
        )

    draft = CvDraft(
        draft_id=hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16],
        job_title=job.title,
        company=job.company,
        sections=sections,
        warnings=warnings,
    )
    _validate_all_items(draft)
    return draft


def apply_cv_edits(
    draft: CvDraft,
    edited_text_by_id: dict[str, str],
) -> CvDraft:
    """Apply editable-preview text only when every claim remains source-backed."""

    if not isinstance(draft, CvDraft):
        raise TypeError("draft must be a CvDraft")
    if not isinstance(edited_text_by_id, dict):
        raise TypeError("edited_text_by_id must be a dictionary")

    known_ids = {item.item_id for item in draft.items}
    unknown_ids = set(edited_text_by_id) - known_ids
    if unknown_ids:
        raise ValueError(f"unknown CV draft item IDs: {', '.join(sorted(unknown_ids))}")

    sections: list[CvDraftSection] = []
    for section in draft.sections:
        items: list[CvDraftItem] = []
        for item in section.items:
            edited_text = edited_text_by_id.get(item.item_id, item.draft_text)
            if not isinstance(edited_text, str):
                raise TypeError("edited CV text must be a string")
            cleaned = _normalize_line(edited_text)
            if not cleaned:
                raise UnsupportedCvEditError(
                    f"{item.item_id} cannot be empty; keep or reword its source content"
                )
            edited_item = item.model_copy(update={"draft_text": cleaned})
            _validate_item(edited_item)
            items.append(edited_item)
        sections.append(section.model_copy(update={"items": items}))
    return draft.model_copy(update={"sections": sections})


def render_cv_draft_text(draft: CvDraft) -> str:
    """Return the current preview as readable plain text for later exporters."""

    blocks: list[str] = []
    for section in draft.sections:
        blocks.append(section.title)
        blocks.extend(f"- {item.draft_text}" for item in section.items)
    return "\n".join(blocks)


def _safe_reword(text: str) -> str:
    value = re.sub(r"^[\s\-*•]+", "", text).strip()
    value = re.sub(r"\s*&\s*", " and ", value)
    value = re.sub(r"^I\s+", "", value, flags=re.IGNORECASE)
    responsibility = re.match(
        r"^Responsible\s+for\s+(?P<verb>[a-z]+)\s+(?P<rest>.+)$",
        value,
        re.IGNORECASE,
    )
    if responsibility:
        replacement = _RESPONSIBILITY_REWRITES.get(
            responsibility.group("verb").casefold()
        )
        if replacement:
            value = f"{replacement} {responsibility.group('rest')}"
    value = _normalize_line(value)
    if value:
        value = value[:1].upper() + value[1:]
    if len(value.split()) >= 5 and value[-1] not in ".!?":
        value += "."
    return value


def _validate_all_items(draft: CvDraft) -> None:
    for item in draft.items:
        _validate_item(item)


def _validate_item(item: CvDraftItem) -> None:
    original_skills = set(_skills_in_text(item.original_text))
    edited_skills = set(_skills_in_text(item.draft_text))
    new_skills = edited_skills - original_skills
    if new_skills:
        raise UnsupportedCvEditError(
            f"{item.item_id} adds unsupported skills: {', '.join(sorted(new_skills))}"
        )

    original_numbers = set(_numbers(item.original_text))
    edited_numbers = set(_numbers(item.draft_text))
    new_numbers = edited_numbers - original_numbers
    if new_numbers:
        raise UnsupportedCvEditError(
            f"{item.item_id} adds unsupported numeric claims: "
            f"{', '.join(sorted(new_numbers))}"
        )

    original_experience = _experience_years(item.original_text)
    edited_experience = _experience_years(item.draft_text)
    if edited_experience and (
        not original_experience or max(edited_experience) > max(original_experience)
    ):
        raise UnsupportedCvEditError(
            f"{item.item_id} adds unsupported years of experience"
        )

    allowed_words = (
        set(_words(item.original_text))
        | set(_words(_safe_reword(item.original_text)))
        | _CONNECTOR_WORDS
    )
    unsupported_words = set(_words(item.draft_text)) - allowed_words
    if unsupported_words:
        raise UnsupportedCvEditError(
            f"{item.item_id} adds unsupported wording: "
            f"{', '.join(sorted(unsupported_words))}"
        )

    original_words = set(_words(item.original_text))
    edited_words = set(_words(item.draft_text))
    removed_qualifiers = (original_words & _PROTECTED_QUALIFIERS) - edited_words
    if removed_qualifiers:
        raise UnsupportedCvEditError(
            f"{item.item_id} removes meaning-changing qualifiers: "
            f"{', '.join(sorted(removed_qualifiers))}"
        )


def _source_lines(text: str) -> list[str]:
    return [
        line
        for raw_line in text.splitlines()
        if (line := _normalize_line(raw_line))
    ]


def _normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _skills_in_text(text: str) -> list[str]:
    return [
        canonical
        for canonical, aliases in SKILL_ALIASES.items()
        if any(_contains_term(text, alias) for alias in aliases)
    ]


def _contains_term(text: str, term: str) -> bool:
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])",
            text,
            re.IGNORECASE,
        )
    )


def _numbers(text: str) -> list[str]:
    return re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?%?", text)


def _experience_years(text: str) -> list[float]:
    return [
        float(value)
        for value in re.findall(
            r"\b(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
            text,
            re.IGNORECASE,
        )
    ]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#]+(?:\.[a-z0-9+#]+)*", text.casefold())


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result
