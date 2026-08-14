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

To work from the current stable branch:

```powershell
git switch main
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

Start the Streamlit application:

```powershell
uv run streamlit run app.py
```

Open the local address shown in the terminal, normally
`http://localhost:8501`. The **CV profile** tab reads and confirms a PDF or
DOCX CV. The **Job search** tab prefills its fields from that saved profile and
runs each selected source independently. Greenhouse, Lever, and Ashby show
their board-name settings when enabled. Source errors are displayed without
stopping the remaining sources. Related jobs are ranked from 0–100 with matched
and missing skills plus a short explanation. The displayed table can be
searched and downloaded as CSV or Excel, and ranked searches are saved locally
in SQLite for later workflow steps.

Select a row in the ranked results table to use the **CV customization** tab.
The customization workflow compares the job with literal evidence from the
uploaded CV, flags requested skills and experience that the original text does
not support, and promotes relevant existing CV lines. It applies only small,
allowlisted wording improvements and provides a line-by-line editable preview.
Every edit is checked against its original source line; new skills, numbers,
experience claims, and unsupported wording are rejected. For privacy, original
CV text and the preview are held only in the active Streamlit session and are
not written to the SQLite database.

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
git switch main
git pull
git switch -c feature/short-task-name
```

Review and save your changes:

```powershell
git status
git diff
git add <changed-files>
git commit -m "type: describe the completed change"
git push -u origin feature/short-task-name
```

Then open GitHub and create a pull request from the feature branch into `main`.
Do not commit `.venv`, `.env`, real CVs, databases, generated CVs, or API
credentials.

## Updating dependencies

After changing a dependency file, synchronize the environment:

```powershell
uv pip install -r requirements.txt
```

For optional AI development, use `requirements-ai.txt` instead.
