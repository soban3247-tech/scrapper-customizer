# Development Plan

This plan turns the existing scraper into the MVP described in
[ARCHITECTURE.md](ARCHITECTURE.md). Check an item when it is implemented and
tested.

## Phase 0: Project Setup

- [x] Write the project proposal and architecture
- [x] Document setup and run commands
- [x] Create the initial dependency list for `uv`
- [x] Add `.gitignore` for `.venv`, generated CVs, databases, and secrets
- [x] Add `.env.example` for optional API keys
- [x] Create the planned package and test directories

**Outcome:** A new developer can install and understand the project.

## Phase 1: Core Models and Scraper Refactor

- [x] Define Pydantic models for `Profile`, `Job`, `SearchConfig`, and `MatchResult`
- [x] Define one common interface for all scraper modules, if any of these are not compatible with the others in terms of interface the interface should be handled in such a way that each of them may have their own interface so they could be switched through UI on runtime on the click of button.
Remember their could be more of these job platforms added from where we could scrape links, so key it the way so that more could be added later without causing errors.
- [x] Move each scraper from `UI.py` into its own file
  - [x] Create the Remotive adapter
  - [x] Create the Arbeitnow adapter
  - [x] Create the Remote OK adapter
  - [x] Create the Greenhouse adapter
  - [x] Create the Lever adapter
  - [x] Create the Ashby adapter
  - [x] Create the HiringCafe adapter
  - [x] Route the application through the registry and remove legacy scraper functions
- [x] Add a scraper registry so the UI can enable sources by name
- [x] Keep HiringCafe, Remotive, Arbeitnow, Remote OK, Greenhouse, Lever, and Ashby
- [ ] Keep LinkedIn as an optional adapter for approved user credentials
- [x] Move normalization, date filtering, and deduplication into core services
- [x] Add tests for job normalization, dates, and duplicate removal

**Outcome:** Every source produces the same `Job` model and can be tested alone.

## Phase 2: CV Upload and Profile Extraction

- [x] Read text from PDF CVs with PyMuPDF
- [x] Read text from DOCX CVs with python-docx
- [x] Extract skills, job titles, experience, education, and likely domain
- [x] Start with a local skill dictionary and explainable matching rules
- [x] Show the extracted profile in an editable form
- [x] Validate the corrected profile with Pydantic
- [ ] Save the profile in SQLite for later sessions
- [ ] Add parser and extraction tests using sample CVs

**Outcome:** The user can upload a CV and confirm an accurate profile.

## Phase 3: Search and Scraping Interface

- [ ] Create the Streamlit application entry point
- [ ] Prefill search fields from the confirmed profile
- [ ] Allow job title, skills, location, date, and page limits to be edited
- [ ] Allow sources to be selected independently
- [ ] Collect any source-specific board names or API credentials
- [ ] Run selected scrapers and show progress and source errors
- [ ] Continue the search when one source fails
- [ ] Remove the Tkinter UI after Streamlit reaches feature parity

**Outcome:** The user can configure and run a multi-source job search.

## Phase 4: Filtering, Ranking, and Results

- [ ] Remove jobs with no meaningful title, domain, or skill relationship
- [ ] Calculate a 0-100 score using title, skills, domain, preferences, and recency
- [ ] Limit the effect of repeated keywords
- [ ] Record matched skills, missing skills, and a short ranking explanation
- [ ] Sort results from highest to lowest score
- [ ] Display results in a searchable table with application links
- [ ] Save normalized jobs and match details to SQLite
- [ ] Export the displayed results to CSV
- [ ] Add ranking tests for strong, weak, and unrelated job descriptions

**Outcome:** Each retained job has a useful score and understandable reason.

## Phase 5: CV Customization

- [ ] Let the user select a job from the results table
- [ ] Compare the job description with the confirmed profile and original CV
- [ ] Reorder and reword relevant CV content without inventing facts
- [ ] Clearly flag requested skills that are absent from the CV
- [ ] Add an editable preview before export
- [ ] Create a simple DOCX template with docxtpl
- [ ] Create a second professional DOCX template
- [ ] Export the selected version as DOCX
- [ ] Add tests that prevent unsupported skills or experience from being added

**Outcome:** The user can review and export an honest, job-focused CV.

## Phase 6: Integration and MVP Release

- [ ] Connect the full upload-to-export workflow
- [ ] Preserve progress while the user moves between screens
- [ ] Add clear empty, loading, success, and failure states
- [ ] Keep secrets out of logs, CSV files, and version control
- [ ] Run unit tests and one complete workflow with sample data
- [ ] Test setup on a clean Windows environment using the README
- [ ] Update documentation to match the final commands and screens
- [ ] Tag the first working release as `v0.1.0`

**Outcome:** A new user can complete the full workflow without editing code.

## After the MVP

- [ ] Add optional LangGraph orchestration for AI-assisted steps
- [ ] Support additional LLM providers and local models
- [ ] Add semantic ranking with embeddings
- [ ] Add more job sources and CV templates
- [ ] Track applications and their status
- [ ] Consider a FastAPI and React interface only if Streamlit becomes limiting

## MVP Rules

- Scraping and basic ranking must work without an AI API.
- One failed scraper must not stop other sources.
- Generated CVs must never invent experience, education, or skills.
- Shared models are the contract between modules.
- Each phase requires focused tests before the next integration step.
