# Job Scraper and CV Customizer Architecture

## Goal

The application helps a job seeker upload a CV, confirm the extracted profile,
search selected job sources, understand ranked matches, and generate an honest
job-focused CV. It must never invent skills, education, or experience.

## System Flow

```text
Next.js frontend
    -> FastAPI routes
    -> CV, scraper, matching, storage, or customization service
    -> shared Pydantic models
    -> JSON response to the frontend
```

The frontend handles presentation and browser state. FastAPI handles HTTP,
validation, and service orchestration. Business modules must not depend on
Next.js or FastAPI so they remain independently testable.

## Project Structure

```text
frontend/
    src/app/                       Next.js pages and layouts
    src/components/                Shared visual components
    src/features/
        cv-upload/                 Upload and profile review UI
        job-search/                Search configuration UI
        job-results/               Ranked results UI
        cv-customizer/             CV preview and export UI
    src/lib/                       FastAPI client and frontend helpers

backend/
    src/job_assistant/
        api/
            main.py                FastAPI entry point
            routes/                Routes grouped by feature
        models/                    Profile, Job, SearchConfig, MatchResult
        resume/                    PDF/DOCX reading and profile extraction
        scrapers/                  One adapter per job source
        matching/                  Filtering, scoring, and explanations
        storage/                   SQLite and file export
        customizer/                CV tailoring and template rendering
    tests/                         Unit and integration tests
    UI.py                          Temporary Tkinter compatibility app
    requirements.txt              Core Python dependencies
    requirements-ai.txt           Optional AI dependencies

docs/                              Project documentation
templates/                         DOCX or HTML CV templates
data/                              Local SQLite files
uploads/                           Private uploaded CVs
outputs/                           Generated CVs and exports
```

## Module Contracts

- Every scraper accepts `SearchConfig` and returns normalized `Job` objects.
- The scraper registry isolates failures so one source cannot stop the others.
- CV parsing produces a validated `Profile` that the user can correct.
- Matching consumes `Profile` and `Job` and produces `MatchResult`.
- Customization consumes confirmed CV facts and one selected job.
- Storage modules own database and export details.
- API routes call services; they do not contain scraping or ranking algorithms.

This separation allows each layer to be developed and tested without running the
frontend or unrelated services.

## Backend API Boundaries

Current and planned endpoints:

```text
GET  /health
POST /profiles/extract
PUT  /profiles/current       planned
GET  /jobs/sources
POST /jobs/search
POST /jobs/rank              planned
POST /resumes/customize      planned
```

Long scraping operations can start synchronously for the MVP. Background jobs
can be introduced later if request duration becomes a real problem.

## Ranking

Initial ranking is local and explainable. It considers title, domain, skills,
location, remote preference, and posting date. Repeated keywords have limited
influence. Each retained job includes a 0-100 score, matched skills, missing
skills, and a short explanation.

## Technology Decisions

- Next.js provides a polished, maintainable web interface.
- FastAPI exposes the existing Python modules without duplicating logic in
  Next.js API routes.
- Pydantic provides consistent validation at module and API boundaries.
- Requests and BeautifulSoup handle standard sources; Playwright is optional.
- PyMuPDF and python-docx read CV files.
- SQLite stores profiles and results for the MVP.
- LangGraph remains optional for later AI-assisted workflow steps.
- pytest verifies backend modules and connected workflows.

LinkedIn remains optional and requires user-provided, approved API access.

## Migration Rule

`backend/UI.py` and `backend/ui/` remain only until the Next.js and FastAPI flow
reaches feature parity. They should receive maintenance fixes only; new product
features belong in the API and Next.js feature directories.
