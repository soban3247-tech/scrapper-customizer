# Job Scraper and CV Customizer

A web application that reads a CV, extracts the candidate's skills and target
roles, searches selected job sources, and displays normalized application links.
Future phases will rank the jobs and generate a tailored CV for a selected role.

## How It Works

1. The user uploads a PDF or DOCX CV in the Next.js frontend.
2. The FastAPI backend extracts skills, job titles, experience, education, and domain.
3. The user reviews the extracted profile and edits the job-search settings.
4. The user selects job sources and starts the search.
5. Each scraper returns jobs in one shared format for the frontend to display.
6. Planned modules will rank jobs, explain each score, and customize the CV.

See [Architecture](docs/ARCHITECTURE.md) and [Development Plan](docs/PLAN.md)
for design decisions and project phases.

## Technology

- **Frontend:** Next.js, React, and TypeScript
- **Backend:** FastAPI, Python, and Pydantic
- **Package managers:** npm for the frontend and `uv` for Python
- **Storage:** SQLite and local output directories
- **Testing:** pytest and ESLint

## Prerequisites

Install these tools before starting:

- [Git](https://git-scm.com/downloads)
- [Node.js 20 or newer](https://nodejs.org/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

On Windows, `uv` can be installed from PowerShell with:

```powershell
winget install --id astral-sh.uv -e
```

Restart PowerShell if the `uv` command is not immediately available.

## First-Time Setup

Open PowerShell and run:

```powershell
git clone https://github.com/soban3247-tech/scrapper-customizer.git
cd scrapper-customizer

uv python install 3.11
uv venv --python 3.11
uv pip install -r backend/requirements.txt
Copy-Item .env.example .env

Set-Location frontend
npm ci
Copy-Item .env.example .env.local
Set-Location ..
```

The default environment files are enough for the current local workflow. Add
credentials to `.env` only for optional services that you choose to use. Never
commit `.env`, `.env.local`, real CVs, or API keys.

Optional AI dependencies:

```powershell
uv pip install -r backend/requirements-ai.txt
```

Playwright's Chromium browser is required only by browser-based scraper modules:

```powershell
uv run playwright install chromium
```

## Run the Project

The frontend and backend run in separate terminals.

**Terminal 1 - backend** (from the repository root):

```powershell
uv run uvicorn job_assistant.api.main:app --app-dir backend/src --reload --port 8000
```

**Terminal 2 - frontend** (from the repository root):

```powershell
Set-Location frontend
npm run dev
```

Open these addresses:

- Web application: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- API health check: `http://localhost:8000/health`

If port `8000` is unavailable, start the backend on another port and update
`NEXT_PUBLIC_API_URL` in `frontend/.env.local` to match it.

## Test the Project

Run backend tests from the repository root:

```powershell
uv run pytest -c backend/pytest.ini
```

Check the frontend from the repository root:

```powershell
Set-Location frontend
npm run lint
npm run build
```

## Project Structure

```text
scrapper-customizer/
|-- backend/
|   |-- src/job_assistant/
|   |   |-- api/           FastAPI routes used by the frontend
|   |   |-- models/        Shared data models
|   |   |-- resume/        CV reading and profile extraction
|   |   |-- scrapers/      Separate adapters for each job source
|   |   |-- matching/      Job filtering, ranking, and explanations
|   |   |-- customizer/    Tailored CV generation
|   |   `-- storage/       Profile, job, and export storage
|   |-- tests/             Backend unit and integration tests
|   |-- UI.py              Temporary legacy Tkinter interface
|   `-- requirements.txt   Core Python dependencies
|-- frontend/
|   |-- src/app/           Next.js pages and global styles
|   |-- src/features/      Feature-specific React components
|   |-- src/lib/           FastAPI client and shared utilities
|   `-- package.json       Frontend dependencies and commands
|-- docs/                  Architecture and development plan
|-- templates/             CV templates
|-- data/                  Local database files (not committed)
|-- uploads/               Uploaded CVs (not committed)
|-- outputs/               Generated files and exports (not committed)
|-- .env.example           Backend environment-variable template
`-- README.md              Project setup and overview
```

The modules are intentionally separate: the frontend calls the API, while CV
extraction, scraping, matching, customization, and storage can be developed and
tested independently behind the backend routes.

## Current Status

CV upload, profile extraction, editable search settings, source selection, and
job searching are connected through the web interface. Relevance filtering,
explainable ranking, CSV export, and tailored CV generation are later phases and
should not be considered complete yet.

The legacy Tkinter application can still be started from the repository root:

```powershell
uv run python backend/UI.py
```
