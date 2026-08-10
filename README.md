# Job Scraper and CV Customizer

A Python application that finds relevant jobs, ranks them against a user's CV,
and helps tailor the CV for a selected role. See [ARCHITECTURE.md](ARCHITECTURE.md)
for the proposed workflow and module design.

## Prerequisites

- Git
- Windows 10 or newer
- Internet access for job sources and package installation

Python does not need to be installed manually because `uv` can install it.

## Setup with uv

### 1. Clone the repository

```powershell
git clone https://github.com/soban3247-tech/scrapper-customizer.git
cd scrapper-customizer
```

### 2. Install uv

```powershell
winget install --id astral-sh.uv -e
```

Restart the terminal if the `uv` command is not immediately available.

### 3. Create the environment and install packages

```powershell
uv python install 3.11
uv venv --python 3.11
uv pip install -r requirements.txt
```

`uv` automatically uses the `.venv` directory, so activation is optional. To
activate it manually in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install the optional browser

This is only needed for scraper modules that use Playwright:

```powershell
uv run playwright install chromium
```

## Run the Current Application

```powershell
uv run python UI.py
```

The current application uses Tkinter, which is included with the Windows Python
installation. After the planned Streamlit interface is added, it will run with:

```powershell
uv run streamlit run app.py
```

## Run Tests

```powershell
uv run pytest
```

## Updating Dependencies

Add or change a package in `requirements.txt`, then run:

```powershell
uv pip install -r requirements.txt
```

Do not commit the `.venv` directory or private API keys.
