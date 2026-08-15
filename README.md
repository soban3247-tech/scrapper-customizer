# Job Scraper and CV Customizer

A web application that extracts a profile from a CV, finds relevant jobs, ranks
them with explainable rules, and helps tailor the CV for a selected role.

- [Architecture](docs/ARCHITECTURE.md)
- [Development plan](docs/PLAN.md)

## Technology

- Next.js for the browser frontend
- FastAPI for the Python HTTP API
- Pydantic models and modular Python services
- SQLite for local application data
- `uv` for Python environments and packages

## Prerequisites

- Git
- Node.js 20 or newer for the future Next.js frontend
- Internet access for dependencies and job sources

Python does not need to be installed manually because `uv` can manage it.

## Backend Setup

Run these commands from the repository root:

```powershell
winget install --id astral-sh.uv -e
uv python install 3.11
uv venv --python 3.11
uv pip install -r backend/requirements.txt
Copy-Item .env.example .env
```

Restart PowerShell if `uv` is not immediately available.

Optional AI dependencies are separate from the core application:

```powershell
uv pip install -r backend/requirements-ai.txt
```

Playwright's browser is only needed by browser-based scraper modules:

```powershell
uv run playwright install chromium
```

## Run the Backend

Start the FastAPI development server:

```powershell
uv run uvicorn job_assistant.api.main:app --app-dir backend/src --reload
```

The API is available at `http://127.0.0.1:8000`, its health endpoint is
`http://127.0.0.1:8000/health`, and interactive API documentation is at
`http://127.0.0.1:8000/docs`.

The original Tkinter scraper remains available during the web migration:

```powershell
uv run python backend/UI.py
```

## Frontend Setup

Install and run the Next.js application:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Keep the FastAPI server running in a separate
terminal so CV extraction and job searches can reach the backend.

The current web workflow supports:

1. Uploading a PDF or DOCX CV.
2. Extracting skills, job titles, experience, education, and domain.
3. Editing the search title, skills, location, and remote preference.
4. Selecting scraper sources and entering source-specific configuration.
5. Running the scrapers and displaying normalized application links.

The extracted search title drives the current scraper queries. Extracted skills
are editable and sent with the search request, but relevance filtering and score
ranking are Phase 4 work; some source results may therefore still be unrelated.

## Run Tests

From the repository root:

```powershell
uv run pytest -c backend/pytest.ini
```

## Project Layout

```text
frontend/                  Next.js pages, components, and feature UI
backend/
    src/job_assistant/
        api/               FastAPI application and routes
        models/            Shared Pydantic data contracts
        resume/            CV reading and profile extraction
        scrapers/          One adapter per job source
        matching/          Job filtering, scoring, and explanations
        customizer/        CV tailoring and rendering
        storage/           SQLite and export repositories
    tests/                 Backend unit and integration tests
    UI.py                  Temporary Tkinter compatibility application
    requirements.txt       Core Python dependencies
docs/                      Architecture and development plan
templates/                 Version-controlled CV templates
data/                      Local database files
uploads/                   Private CV uploads
outputs/                   Generated CVs and job exports
```

The contents of `data/`, `uploads/`, and `outputs/`, plus `.env`, are ignored by
Git. Never commit real CVs, generated documents, databases, or credentials.

## Updating Dependencies

After editing a Python dependency file:

```powershell
uv pip install -r backend/requirements.txt
```

Frontend dependencies are managed by `frontend/package.json` and
`frontend/package-lock.json`.
