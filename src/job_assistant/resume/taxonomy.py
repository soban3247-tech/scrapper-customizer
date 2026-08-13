"""Local, version-controlled terms used for explainable CV extraction."""

from dataclasses import dataclass


# Canonical names are returned to the Profile model. Aliases are matched without
# regard to case, but only as complete terms so short skills do not match inside
# unrelated words.
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript",),
    "Java": ("java",),
    "C#": ("c#", "c sharp"),
    "C++": ("c++",),
    "Go": ("golang",),
    "Rust": ("rust",),
    "SQL": ("sql",),
    "HTML": ("html", "html5"),
    "CSS": ("css", "css3"),
    "React": ("react", "react.js", "reactjs"),
    "Angular": ("angular",),
    "Vue.js": ("vue", "vue.js", "vuejs"),
    "Node.js": ("node", "node.js", "nodejs"),
    "Django": ("django",),
    "Flask": ("flask",),
    "FastAPI": ("fastapi",),
    ".NET": (".net", "dotnet"),
    "REST APIs": ("rest api", "rest apis", "restful api", "restful apis"),
    "GraphQL": ("graphql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "MongoDB": ("mongodb",),
    "Redis": ("redis",),
    "Git": ("git",),
    "Linux": ("linux",),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "Terraform": ("terraform",),
    "Jenkins": ("jenkins",),
    "GitHub Actions": ("github actions",),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "Google Cloud": ("gcp", "google cloud", "google cloud platform"),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch",),
    "Apache Spark": ("apache spark", "pyspark"),
    "Power BI": ("power bi",),
    "Tableau": ("tableau",),
    "Excel": ("microsoft excel", "excel"),
    "Figma": ("figma",),
    "Adobe XD": ("adobe xd",),
    "Selenium": ("selenium",),
    "Playwright": ("playwright",),
    "Pytest": ("pytest",),
    "Jira": ("jira",),
    "Agile": ("agile",),
    "Scrum": ("scrum",),
}


TITLE_ALIASES: dict[str, tuple[str, ...]] = {
    "Software Engineer": ("software engineer",),
    "Software Developer": ("software developer",),
    "Backend Engineer": ("backend engineer", "back-end engineer"),
    "Backend Developer": ("backend developer", "back-end developer"),
    "Frontend Engineer": ("frontend engineer", "front-end engineer"),
    "Frontend Developer": ("frontend developer", "front-end developer"),
    "Full Stack Engineer": (
        "full stack engineer",
        "full-stack engineer",
    ),
    "Full Stack Developer": (
        "full stack developer",
        "full-stack developer",
    ),
    "Mobile Developer": ("mobile developer", "application developer"),
    "Data Engineer": ("data engineer",),
    "Data Scientist": ("data scientist",),
    "Data Analyst": ("data analyst",),
    "Machine Learning Engineer": (
        "machine learning engineer",
        "ml engineer",
    ),
    "DevOps Engineer": ("devops engineer",),
    "Cloud Engineer": ("cloud engineer",),
    "Site Reliability Engineer": (
        "site reliability engineer",
        "sre engineer",
    ),
    "QA Engineer": ("qa engineer", "quality assurance engineer"),
    "Test Engineer": ("test engineer", "automation engineer"),
    "Security Engineer": ("security engineer",),
    "Cybersecurity Analyst": (
        "cybersecurity analyst",
        "cyber security analyst",
        "security analyst",
    ),
    "Business Analyst": ("business analyst",),
    "Product Manager": ("product manager",),
    "Project Manager": ("project manager",),
    "UI Designer": ("ui designer", "user interface designer"),
    "UX Designer": ("ux designer", "user experience designer"),
    "Product Designer": ("product designer",),
}


@dataclass(frozen=True, slots=True)
class DomainRule:
    """Evidence terms used to score one possible career domain."""

    skills: frozenset[str]
    titles: frozenset[str]


DOMAIN_RULES: dict[str, DomainRule] = {
    "Software Engineering": DomainRule(
        skills=frozenset(
            {
                "Python",
                "JavaScript",
                "TypeScript",
                "Java",
                "C#",
                "C++",
                "Go",
                "Rust",
                "HTML",
                "CSS",
                "React",
                "Angular",
                "Vue.js",
                "Node.js",
                "Django",
                "Flask",
                "FastAPI",
                ".NET",
                "REST APIs",
                "GraphQL",
            }
        ),
        titles=frozenset(
            {
                "Software Engineer",
                "Software Developer",
                "Backend Engineer",
                "Backend Developer",
                "Frontend Engineer",
                "Frontend Developer",
                "Full Stack Engineer",
                "Full Stack Developer",
                "Mobile Developer",
            }
        ),
    ),
    "Data and AI": DomainRule(
        skills=frozenset(
            {
                "Python",
                "SQL",
                "Pandas",
                "NumPy",
                "scikit-learn",
                "TensorFlow",
                "PyTorch",
                "Apache Spark",
                "Power BI",
                "Tableau",
                "Excel",
            }
        ),
        titles=frozenset(
            {
                "Data Engineer",
                "Data Scientist",
                "Data Analyst",
                "Machine Learning Engineer",
            }
        ),
    ),
    "DevOps and Cloud": DomainRule(
        skills=frozenset(
            {
                "Linux",
                "Docker",
                "Kubernetes",
                "Terraform",
                "Jenkins",
                "GitHub Actions",
                "AWS",
                "Azure",
                "Google Cloud",
            }
        ),
        titles=frozenset(
            {
                "DevOps Engineer",
                "Cloud Engineer",
                "Site Reliability Engineer",
            }
        ),
    ),
    "Quality Assurance": DomainRule(
        skills=frozenset({"Selenium", "Playwright", "Pytest"}),
        titles=frozenset({"QA Engineer", "Test Engineer"}),
    ),
    "Cybersecurity": DomainRule(
        skills=frozenset({"Linux", "Python"}),
        titles=frozenset({"Security Engineer", "Cybersecurity Analyst"}),
    ),
    "Product and Project Management": DomainRule(
        skills=frozenset({"Jira", "Agile", "Scrum"}),
        titles=frozenset(
            {"Business Analyst", "Product Manager", "Project Manager"}
        ),
    ),
    "Product Design": DomainRule(
        skills=frozenset({"Figma", "Adobe XD"}),
        titles=frozenset({"UI Designer", "UX Designer", "Product Designer"}),
    ),
}
