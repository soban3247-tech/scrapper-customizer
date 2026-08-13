# Job Scraper and CV Customizer

## Project Proposal

This application helps a job seeker find relevant vacancies and tailor their CV
for a selected role. The user uploads a CV, reviews the detected skills and job
preferences, chooses job sources, and receives a ranked list of suitable jobs.

The first version will stay simple, explain its decisions, and never add skills
or experience that are not present in the original CV.

## User Workflow

1. Upload a PDF or DOCX CV.
2. Extract skills, experience, job titles, and likely career domain.
3. Let the user review and edit the extracted profile.
4. Prefill the job search form that profile.
5. Scrape jobs from the sources selected by the user.
6. Remove duplicates and clearly unrelated jobs.
7. Rank the remaining jobs and explain each score.
8. Save the results to CSV and display them in the application.
9. Let the user select a job and customize their CV for it.
10. Review the customized CV and export it using a template.

## Suggested Technology

- Python for the application and business logic
- Streamlit for the initial user interface
- Pydantic for shared data models and validation
- Requests and BeautifulSoup for scraping
- Playwright only for sources that require a browser
- PyMuPDF and python-docx for reading CVs
- scikit-learn for initial keyword and TF-IDF ranking
- SQLite for application data and Pandas for CSV export
- docxtpl for editable DOCX templates / HTML templates connected with backend
- LangGraph for optional AI workflow orchestration
- pytest for automated tests

LangGraph should coordinate only AI-assisted steps such as profile extraction and
CV customization. Scraping, filtering, storage, and basic ranking must continue to
work without an AI service.

## Module Structure

```text
app.py                              Streamlit application entry point
ui/                                 Upload, search, results, and CV review screens
src/job_assistant/
    models/                         Shared Profile and Job data models
    resume/                         CV reading and profile extraction
    scrapers/                       One adapter for each job source
    matching/                       Filtering, scoring, and explanations
    storage/                        SQLite storage and CSV export
    customizer/                     CV tailoring and template rendering
templates/                          Version-controlled DOCX templates
tests/unit/                         Tests for individual modules
tests/integration/                  Tests for connected workflows
tests/fixtures/                     Synthetic and anonymized test data
data/                               Local application database
uploads/                            Private CV uploads
outputs/                            Generated CVs and result exports
```

The contents of `data/`, `uploads/`, and `outputs/` are local-only and excluded
from version control. This prevents private CVs, generated documents, and
database records from being uploaded to GitHub.

Every scraper returns the same `Job` model. Other modules work with that model
instead of depending directly on individual scrapers. This makes each source easy
to develop, test, replace, or disable independently.

LinkedIn will be an optional adapter for users who have approved API access and
provide their own credentials. It will not be required for the application.

## Ranking Approach

The first ranking system will use explainable rules instead of relying entirely
on an AI model. It will consider:

- Job title and domain match
- Required skills found in the CV
- Location and remote-work preferences
- Posting date
- Important skills that are missing

Each result will include a score and a short reason, for example:

> 82% match: title matches and 7 of 9 requested skills were found; AWS and Docker
> were not found in the CV.

Repeated keywords will have a limited effect so keyword stuffing cannot produce
an unrealistic score.

## Development Phases

### Phase 1: Foundation

Split the existing `UI.py` into shared models, individual scrapers, matching, and
storage modules without changing its current scraping behavior.

### Phase 2: CV Profile and Ranking

Add CV upload, editable profile extraction, job filtering, ranking explanations,
CSV storage, and a results screen.

### Phase 3: CV Customization

Add job-specific CV rewriting, user review, and one DOCX template. The system must
only reword or reorganize facts found in the original CV.

### Later Improvements

Add more templates, additional job sources, stronger semantic ranking, optional
LLM providers, application tracking, and a more scalable web interface if needed.

## MVP Success Criteria

The MVP is complete when a user can upload a CV, correct the extracted profile,
scrape selected sources, understand the ranking of each job, export results to
CSV, and produce a reviewed DOCX CV for one selected job.
