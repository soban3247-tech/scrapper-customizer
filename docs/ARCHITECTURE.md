# Job Scraper and CV Customizer Architecture

## Goal

The application helps a job seeker upload a CV, confirm the extracted profile,
search selected job sources, understand ranked matches, and generate an honest
job-focused CV. It must never invent skills, education, or experience.

This document separates the **current implementation** from the **planned
architecture**. Planned decisions may change during the required phase review in
[IMPLEMENTATION_ORDER.md](IMPLEMENTATION_ORDER.md).

## Current Implementation

```text
Next.js frontend
    -> current FastAPI routes
    -> CV extraction or scraper service
    -> shared Pydantic models
    -> JSON response to the frontend
```

The current web workflow supports CV extraction, editable search settings,
source selection, and normalized job search. The backend has a local SQLite
profile repository, but the web workflow does not yet provide authenticated
profile persistence. Authentication, Supabase, ranking, saved results, CSV
export, and CV customization are not implemented yet.

## Planned Hosted Flow

```text
Authenticated user
    -> Next.js frontend and Supabase Auth session
    -> FastAPI with bearer access token
    -> auth and ownership validation
    -> CV, scraper, matching, storage, or customization service
    -> Supabase Postgres and shared Pydantic models
    -> user-owned JSON, CSV, or DOCX response
```

The frontend handles presentation and browser state. FastAPI handles HTTP,
validation, ownership, and service orchestration. Supabase Auth provides user
identity, and Supabase Postgres is the planned hosted database.

Business modules must not depend on Next.js, FastAPI, or Supabase-specific HTTP
APIs. They consume shared models and repository interfaces so they remain
independently testable.

## Project Structure

```text
frontend/
    src/app/                       Next.js pages and layouts
    src/components/                Shared visual components
    src/features/
        cv-upload/                 Upload and profile review UI
        job-search/                Search configuration UI
        job-results/               Ranked results UI (planned Phase 4)
        cv-customizer/             CV preview and export UI (planned Phase 5)
    src/lib/                       FastAPI client and frontend helpers

backend/
    src/job_assistant/
        api/
            main.py                FastAPI entry point
            routes/                Routes grouped by feature
        models/                    Profile, Job, SearchConfig, MatchResult
        resume/                    PDF/DOCX reading and profile extraction
        scrapers/                  One adapter per job source
        matching/                  Filtering and scoring (planned Phase 4)
        storage/                   Current SQLite and planned Postgres repositories
        customizer/                CV tailoring (planned Phase 5)
    tests/                         Unit and integration tests
    UI.py                          Temporary Tkinter compatibility app
    requirements.txt              Core Python dependencies
    requirements-ai.txt           Optional AI dependencies

docs/                              Project documentation
templates/                         Version-controlled CV templates
data/                              Current local SQLite files
uploads/                           Private local uploads, not committed
outputs/                           Generated local files, not committed
```

## Module Contracts

- Every scraper accepts `SearchConfig` and returns normalized `Job` objects.
- The scraper registry isolates failures so one source cannot stop the others.
- CV parsing produces a validated `Profile` that the user can correct.
- Matching consumes a confirmed `Profile` and normalized `Job` and produces a
  `MatchResult`.
- Customization consumes confirmed CV facts, stored source text, and one selected
  job; it does not call the ranking algorithm.
- The persisted `job_id` is the planned Phase 4 to Phase 5 handoff.
- Storage modules own database and export details behind repository interfaces.
- API routes call services; they do not contain extraction, scraping, ranking, or
  customization algorithms.

Shared model or API changes require the contract-change process documented in
[IMPLEMENTATION_ORDER.md](IMPLEMENTATION_ORDER.md).

## Authentication and Data Ownership

Supabase Auth and Postgres are planned in Phase 3.5. The browser sends the
Supabase access token in the `Authorization` header. FastAPI validates the token
and derives the user ID from its subject; request bodies must never choose a user
ID.

Planned user-owned data boundaries are:

- One current confirmed profile and extracted CV text per user.
- Search runs belonging to the user who initiated them.
- Normalized jobs and match results belonging to a search run.
- Generated drafts kept in browser state for the MVP.
- Generated DOCX files returned as downloads rather than retained permanently.

Extracted CV text is sensitive personal data. FastAPI queries and Supabase Row
Level Security must prevent cross-user access. Profile deletion must also remove
the user's stored CV text according to the final migration policy. Raw uploaded
CV files are not planned for permanent storage.

## Backend API Boundaries

Current endpoints:

```text
GET  /health
POST /profiles/extract
GET  /jobs/sources
POST /jobs/search
```

Planned authenticated endpoints and changes:

```text
POST   /profiles/extract                 save extracted text and initial profile
GET    /profiles/current                 load the confirmed profile
PUT    /profiles/current                 save profile corrections
DELETE /profiles/current                 remove profile and stored CV text
POST   /jobs/search                      return search_id and persist jobs
POST   /jobs/rank                        rank jobs from a user-owned search_id
GET    /jobs/results/{search_id}         restore ranked results
GET    /jobs/results/{search_id}/csv     export displayed ranked results
GET    /resumes/templates                list templates and LLM availability
POST   /resumes/customize                create an editable structured draft
POST   /resumes/export                   validate and return a DOCX
```

Long scraping and customization operations can remain synchronous for the MVP.
Background jobs should be introduced only when measured request duration makes
them necessary.

## Planned Ranking

Initial ranking is local and explainable. It considers title, domain, skills,
location, remote preference, and posting date. Repeated keywords have limited
influence. Each retained job includes a 0-100 score, matched skills, missing
skills, component scores, and a short explanation.

Ranking must work without an AI service. Stored results and CSV exports remain
scoped to the authenticated user and preserve the ordering displayed in the UI.

## Planned Customization

Rules mode is the default and must work without an AI service. It selects and
reorders existing CV content based on the selected job and clearly flags skills
that the job requests but the CV does not support.

An optional LLM mode may reword existing content when a server-side API key is
configured. LLM output is untrusted and must be checked against source facts,
must not introduce unsupported skills or numerical claims, and must be shown in
an editable preview before export. API keys never enter browser state or logs.

Two version-controlled DOCX templates are planned. Template rendering is
separate from content selection so templates can be added without modifying the
customization rules.

## Technology Decisions

- Next.js provides the browser interface.
- FastAPI exposes Python business modules without duplicating them in Next.js
  routes.
- Pydantic defines and validates module and API contracts.
- Requests and BeautifulSoup handle standard sources; Playwright is optional.
- PyMuPDF and python-docx read CV files.
- SQLite is the current local storage implementation.
- Supabase Postgres and Auth are the planned hosted persistence and identity
  services, introduced through migrations in Phase 3.5.
- SQLAlchemy repositories and Alembic migrations are planned to isolate database
  details and keep schema changes reviewable.
- Basic ranking and rules-based customization do not require an LLM.
- Optional AI dependencies remain separate from core requirements.
- pytest verifies backend modules and connected workflows.

LinkedIn remains optional and requires user-provided, approved API access.

## Migration and Change Rules

`backend/UI.py` and `backend/ui/` remain only until the Next.js and FastAPI flow
reaches feature parity. They receive maintenance fixes only; new product features
belong in the API and Next.js feature directories.

Supabase is a planned decision, not completed work. Before Phase 3.5 or either
parallel phase begins, both developers must review the relevant plan. Any change
to authentication, persistence, shared models, database schema, public API, or
the `job_id` handoff must be documented and agreed before implementation.
