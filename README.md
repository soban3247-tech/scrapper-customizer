# Job Scraper and CV Customizer

A Python application that finds relevant jobs, ranks them against a user's CV,
and helps tailor the CV for a selected role. The MVP uses explainable matching
rules and must never add experience, education, or skills that are absent from
the original CV.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the workflow and module design, and
[PLAN.md](PLAN.md) for the implementation checklist.

## Prerequisites

- Git
- Windows 10 or newer
- Internet access for package installation and job sources

Python does not need to be installed manually because `uv` can install and
manage the required version.

## First-time setup with uv

### 1. Clone the repository

```powershell
cd D:\SaaS
git clone https://github.com/soban3247-tech/scrapper-customizer.git
cd scrapper-customizer
```

To work from the current planning branch:

```powershell
git switch agent/project-planning
```

### 2. Install uv

```powershell
winget install --id astral-sh.uv -e
```

Restart PowerShell if `uv` is not immediately available.

### 3. Install Python and the required packages

```powershell
uv python install 3.11
uv venv --python 3.11
uv pip install -r requirements.txt
```

Activation is optional when commands are prefixed with `uv run`. To activate the
environment manually in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Create the local configuration

```powershell
Copy-Item .env.example .env
```

The core scraper does not require an AI key. Add credentials to `.env` only when
you intentionally enable an optional integration. The `.env` file is ignored by
Git.

### 5. Install the optional browser

This is needed only by scraper modules that use Playwright:

```powershell
uv run playwright install chromium
```

### 6. Install optional AI packages

The MVP's scraping and basic ranking work without these packages. Install them
only when developing AI-assisted profile extraction or CV customization:

```powershell
uv pip install -r requirements-ai.txt
```

## Run the application

The current application uses Tkinter:

```powershell
uv run python UI.py
```

After the planned Streamlit interface is implemented, run it with:

```powershell
uv run streamlit run app.py
```

## Run tests

```powershell
uv run pytest
```

## Project layout

```text
src/job_assistant/   Core models and business logic
ui/                  Streamlit screens and session-state helpers
tests/unit/          Fast tests for individual functions and classes
tests/integration/   Tests for workflows across multiple modules
tests/fixtures/      Synthetic and anonymized test inputs only
templates/           Version-controlled DOCX templates
data/                Local SQLite data (contents ignored by Git)
uploads/             Private user CVs (contents ignored by Git)
outputs/             Generated CVs and exports (contents ignored by Git)
```

## Everyday Git workflow

Start a branch for one focused piece of work:

```powershell
git switch agent/project-planning
git pull
git switch -c feature/project-foundation
```

Review and save your changes:

```powershell
git status
git diff
git add README.md PLAN.md .gitignore .env.example
git commit -m "chore: complete project foundation"
git push -u origin feature/project-foundation
```

Then open GitHub and create a pull request from the feature branch into
`agent/project-planning`. Do not commit `.venv`, `.env`, real CVs, databases,
generated CVs, or API credentials.

## Updating dependencies

After changing a dependency file, synchronize the environment:

```powershell
uv pip install -r requirements.txt
```

For optional AI development, use `requirements-ai.txt` instead.
