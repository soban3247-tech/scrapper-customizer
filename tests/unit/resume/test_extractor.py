import pytest

from job_assistant.resume import extract_profile, extract_profile_with_evidence


BACKEND_CV = """
Malik Soban Rabbani
Senior Backend Developer

SUMMARY
Backend specialist with 6+ years of professional experience building REST APIs.

SKILLS
Python, FastAPI, Django, PostgreSQL, Docker, AWS, Git

EXPERIENCE
Senior Backend Developer | Example Systems
Built Python services with FastAPI and PostgreSQL.

EDUCATION
BS Computer Science, University of Example, 2018
"""


def test_extracts_profile_fields_from_backend_cv() -> None:
    profile = extract_profile(BACKEND_CV)

    assert profile.skills == [
        "Python",
        "Django",
        "FastAPI",
        "REST APIs",
        "PostgreSQL",
        "Git",
        "Docker",
        "AWS",
    ]
    assert profile.job_titles == ["Senior Backend Developer"]
    assert profile.years_experience == 6
    assert profile.education == [
        "BS Computer Science, University of Example, 2018"
    ]
    assert profile.domain == "Software Engineering"


def test_uses_title_evidence_to_select_data_domain() -> None:
    profile = extract_profile(
        """
        Data Analyst
        3 years of experience
        Skills: Python, SQL, Excel, Power BI, Tableau
        Master of Data Science - Example University
        """
    )

    assert profile.job_titles == ["Data Analyst"]
    assert profile.years_experience == 3
    assert profile.domain == "Data and AI"
    assert profile.education == ["Master of Data Science - Example University"]


def test_recognizes_skill_aliases_as_canonical_names() -> None:
    profile = extract_profile(
        "Built services with node.js, ReactJS, GCP, k8s, dotnet and sklearn."
    )

    assert profile.skills == [
        "React",
        "Node.js",
        ".NET",
        "Kubernetes",
        "Google Cloud",
        "scikit-learn",
    ]


def test_does_not_match_short_terms_inside_other_words() -> None:
    profile = extract_profile(
        "Managed agile projects and designed cloud migration goals."
    )

    assert "Go" not in profile.skills
    assert "C#" not in profile.skills


def test_chooses_largest_explicit_experience_value() -> None:
    profile = extract_profile(
        "5 years of experience in engineering; experience: 7.5 years overall."
    )

    assert profile.years_experience == 7.5


def test_ignores_implausible_experience_values() -> None:
    profile = extract_profile("Software Developer with 99 years of experience")

    assert profile.years_experience is None


def test_extracts_only_degree_bearing_education_lines() -> None:
    profile = extract_profile(
        """
        EDUCATION
        Bachelor of Software Engineering | Example University | 2020
        Online course in communication
        Diploma in Project Management, Example College
        """
    )

    assert profile.education == [
        "Bachelor of Software Engineering | Example University | 2020",
        "Diploma in Project Management, Example College",
    ]


def test_returns_no_domain_when_top_scores_are_tied() -> None:
    profile = extract_profile("Skills: Python")

    assert profile.domain is None


def test_exposes_auditable_extraction_evidence() -> None:
    result = extract_profile_with_evidence(BACKEND_CV)

    assert result.evidence.skill_matches["Python"] == ("Python",)
    assert "6+ years of professional experience" in (
        phrase.casefold() for phrase in result.evidence.experience_phrases
    )
    assert result.evidence.domain_scores["Software Engineering"] > 0
    with pytest.raises(TypeError):
        result.evidence.domain_scores["Software Engineering"] = 0


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_rejects_empty_cv_text(text: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        extract_profile(text)


def test_rejects_non_string_cv_text() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        extract_profile(None)  # type: ignore[arg-type]
