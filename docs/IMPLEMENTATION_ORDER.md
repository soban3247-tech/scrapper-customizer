# Implementation Order for Phases 4 and 5

> **Living document:** This is the current agreed implementation order, not a
> fixed specification. Before a phase starts, both developers must review its
> scope, contracts, ownership, and acceptance tests. Record approved changes in
> the decision log before changing code.

This document explains how two developers can build Phases 4 and 5 in parallel
without silently changing shared contracts or repeatedly editing the same files.
[PLAN.md](PLAN.md) remains the checklist for implementation status, while this
document controls work order, ownership, and integration.

## Current State

The repository currently supports:

- PDF and DOCX upload with local, rule-based profile extraction.
- Editable search settings in the Next.js interface.
- FastAPI source discovery and normalized multi-source job search.
- Local SQLite profile storage in the backend module.

The following are not implemented yet:

- Authenticated users and user-owned hosted data.
- The confirmed-profile web API and restored frontend sessions.
- Supabase Postgres persistence or database migrations.
- Job filtering, ranking, explanations, saved results, and CSV export.
- CV customization, editable previews, and DOCX export.

The remaining legacy UI cleanup in Phase 3 is independent and must not be mixed
into the Phase 4 or Phase 5 feature branches.

## Required Work Order

```text
Clean, reviewed base branch
            |
            v
Shared foundation: Supabase Auth, Postgres, contracts, frontend boundaries
            |
            +-------------------------------+
            |                               |
            v                               v
Developer A: Phase 4              Developer B: Phase 5
ranking and job results            customization and DOCX
            |                               |
            +---------------+---------------+
                            v
                 Phase 4/5 integration
                            |
                            v
                       Phase 6 work
```

Phases 4 and 5 may start in parallel only after the shared foundation is merged
and both developers create their branches from the same base commit.

## Before Starting Any Phase

Both developers must complete this checklist together:

- [ ] Re-read the relevant section of [PLAN.md](PLAN.md).
- [ ] Confirm the phase goal, exclusions, API contract, and data ownership.
- [ ] Review any decisions recorded since the previous phase.
- [ ] Confirm that required foundation work is merged and tested.
- [ ] Confirm branch names and file ownership.
- [ ] Agree on acceptance tests and sample fixtures.
- [ ] Record approved changes in the decision log below.
- [ ] Update PLAN or ARCHITECTURE first if the agreed behavior has changed.

Do not start implementation while a shared contract is still under discussion.

## Stage 1: Shared Foundation

Target integration branch: `foundation/supabase-auth-persistence`

This stage is planned work and does not describe the current implementation.
Use two short child branches so both developers can contribute without sharing a
working branch:

| Owner | Branch | Responsibilities |
| --- | --- | --- |
| Developer A | `foundation/backend-auth-persistence` | FastAPI JWT validation, SQLAlchemy and Alembic setup, Supabase Postgres repositories, profile ownership, and backend tests |
| Developer B | `foundation/frontend-auth-boundaries` | Supabase sign-in/session UI, bearer-token API client, and separation of the current workflow into feature components |

Merge both child branches into `foundation/supabase-auth-persistence`, run the
foundation acceptance tests, and then merge that branch into `main` before
creating either phase branch.

### Foundation Implementation Order

1. Freeze `Profile`, `Job`, `SearchConfig`, and `MatchResult` as the shared
   contracts for both phases.
2. Define the planned request and response schemas listed under API contracts.
3. Add Supabase authentication to Next.js and verify its bearer JWT in FastAPI.
4. Use the JWT subject as the application `user_id`; never accept a user ID from
   request data.
5. Add SQLAlchemy repositories, a Supabase Postgres connection, and Alembic
   migrations for profiles, search runs, jobs, and matches.
6. Save the validated profile and extracted CV text under the authenticated user.
7. Complete load, update, and delete operations for the current profile.
8. Split the current combined frontend workflow into `cv-upload`, `job-search`,
   and `job-results` feature boundaries without changing behavior.
9. Confirm that no Supabase service-role key or LLM key reaches browser code.

### Planned Persistence Boundaries

- `profiles`: one current profile per user, including validated profile JSON,
  extracted CV text, source filename, and update time.
- `search_runs`: user-owned search configuration and creation time.
- `jobs`: normalized jobs belonging to a search run.
- `matches`: score and explanation belonging to a stored job.
- Generated DOCX files are returned to the user and are not retained for the MVP.

Extracted CV text is sensitive personal data. Every read, write, update, export,
and delete must be scoped to the authenticated user. Supabase Row Level Security
provides defense in depth; FastAPI must still enforce ownership in its queries.

## Planned API Contracts

All endpoints below, except those marked current, require `Authorization: Bearer
<access-token>` after the shared foundation is implemented.

### Profiles

- `POST /profiles/extract` (current, authentication planned): accepts a PDF or
  DOCX, extracts a `Profile`, and plans to save the extracted text and initial
  profile for the authenticated user.
- `GET /profiles/current` (planned): returns the authenticated user's saved
  profile, but never returns the stored raw CV text to the browser.
- `PUT /profiles/current` (planned): validates and saves user corrections to the
  current profile without replacing the stored CV text.
- `DELETE /profiles/current` (planned): deletes the user's profile and stored CV
  text, with dependent searches and results handled by the database policy.

### Search and Ranking

- `POST /jobs/search` (current, response extension planned): runs selected
  scrapers; the planned response adds `search_id` and persists normalized jobs.
- `POST /jobs/rank` (planned): accepts `search_id`, loads the user's confirmed
  profile and stored jobs, and returns ordered `MatchResult` objects.
- `GET /jobs/results/{search_id}` (planned): restores one user-owned ranked run.
- `GET /jobs/results/{search_id}/csv` (planned): exports the displayed ranked
  results with the same order and filters as the UI.

### CV Customization

- `GET /resumes/templates` (planned): lists available templates and whether the
  optional LLM mode is available.
- `POST /resumes/customize` (planned): accepts `job_id`, `template_id`, and mode
  `rules` or `llm`; it loads the authenticated user's profile, stored CV text,
  and selected job and returns an editable structured draft plus warnings.
- `POST /resumes/export` (planned): validates an edited draft and template choice
  and returns a DOCX download.

The Phase 4 to Phase 5 handoff is the persisted `job_id`. Phase 5 must not depend
on Phase 4's internal scoring functions or frontend component state.

## Stage 2A: Developer A - Phase 4

Branch: `feature/phase-4-ranking`

Developer A owns the feature end to end:

- Local, explainable filtering and 0-100 scoring in `matching/`.
- Repeated-keyword limits, matched and missing skills, and explanations.
- Search-run, job, and match repositories plus CSV export.
- Ranking and result endpoints under `/jobs`.
- The `frontend/src/features/job-results/` feature.
- A stable `onCustomize(jobId)` handoff for Phase 5.

Developer A must not implement CV rewriting, template rendering, or customizer
UI. Any required change to a shared model or planned API contract follows the
contract-change process below.

### Phase 4 Merge Gate

- Strong matches rank above weak matches; unrelated jobs are removed.
- Scores remain within 0-100 and repeated terms cannot dominate a score.
- Missing descriptions and dates are handled predictably.
- Results contain matched skills, missing skills, and a useful explanation.
- Saved searches and CSV exports are accessible only to their owner.
- CSV ordering matches the displayed ordering and safely escapes text.
- Backend tests, frontend lint, and frontend build pass.

## Stage 2B: Developer B - Phase 5

Branch: `feature/phase-5-customization`

Developer B develops against fixed `Profile`, `Job`, and stored-CV fixtures, so
work can proceed without waiting for the Phase 4 ranking algorithm.

Developer B owns:

- Rule-based selection and ordering of existing CV content in `customizer/`.
- Optional LLM rewriting when the server has `OPENAI_API_KEY` configured.
- Unsupported-skill warnings and validation against stored CV facts.
- Template discovery, customization, and DOCX export endpoints.
- Two professional DOCX templates.
- The `frontend/src/features/cv-customizer/` preview and export feature.

Rules mode is always available and must not invent facts. LLM output is
untrusted: rewritten items must retain links to source content, numerical claims
must be preserved, newly claimed skills must be rejected, and the user must
review an editable preview before export. The LLM key remains server-side.

Developer B must not change ranking behavior, job-result persistence, or the
results table beyond the agreed `onCustomize(jobId)` integration point.

### Phase 5 Merge Gate

- Rules mode works with no LLM dependency or API key.
- Missing job skills are warnings and are never inserted as candidate skills.
- Malformed, unavailable, or unsupported LLM output fails safely or falls back
  to rules mode without silently adding content.
- Both templates generate DOCX files that can be opened and edited.
- A user cannot customize another user's job or access another user's CV text.
- Backend tests, frontend lint, and frontend build pass.

## File Ownership and Conflict Prevention

| Area | Primary owner during parallel work |
| --- | --- |
| `backend/src/job_assistant/matching/` and Phase 4 tests | Developer A |
| Job-result storage/export and `/jobs` ranking routes | Developer A |
| `frontend/src/features/job-results/` | Developer A |
| `backend/src/job_assistant/customizer/` and Phase 5 tests | Developer B |
| `/resumes` routes, schemas, and DOCX templates | Developer B |
| `frontend/src/features/cv-customizer/` | Developer B |
| Shared models, API client, application bootstrap, migrations, dependency locks, global CSS | Protected shared files |

Protected shared files require advance notice and review from the other
developer. Prefer a small contract PR over including shared changes inside a
large feature PR.

## Git and Merge Order

1. Commit or remove unrelated local files before creating team branches.
2. Merge both foundation child branches into
   `foundation/supabase-auth-persistence`.
3. Merge the tested foundation branch into `main`.
4. Create both phase branches from that same `main` commit.
5. Each developer opens a draft PR early and keeps its contract notes current.
6. Merge current `main` into long-running shared branches; do not force-push a
   rebased branch after review has begun.
7. Merge Phase 4 first because it provides the selectable `job_id` in the real
   results UI.
8. Merge current `main` into Phase 5 and connect the existing customization
   feature through `onCustomize(jobId)`.
9. Merge Phase 5, then use a small integration PR for cross-feature fixes and
   documentation updates. Do not hide new feature work in that PR.

Each PR must contain focused tests and must not include unrelated formatting,
generated files, real CVs, credentials, databases, or outputs.

## Contract-Change Process

When a proposed change affects authentication, shared models, database schema,
API requests or responses, or the Phase 4/5 handoff:

1. Pause only the work affected by the change.
2. Add a proposed entry to the decision log with impacted branches.
3. Both developers review and approve the new contract.
4. Update PLAN, ARCHITECTURE, and this document where applicable.
5. Implement the contract in a small separate PR with tests.
6. Merge it into `main`, then merge `main` into both phase branches.
7. Resume dependent work only after both branches use the same contract.

A change contained entirely inside one owned module needs normal review and a
decision-log entry only when it changes the promised behavior of that phase.

## Final Integration Gate

Before Phase 4 and Phase 5 are considered integrated:

- An authenticated user can upload a CV, correct and restore the profile, search
  jobs, rank them, select a result, customize the CV, edit the preview, and
  download either template.
- A second user cannot access the first user's profile, CV text, jobs, matches,
  CSV, draft, or export.
- Empty, loading, validation, source-failure, unavailable-LLM, and export-failure
  states are visible and recoverable.
- The backend test suite, frontend lint, and production frontend build pass.
- One complete browser workflow passes with synthetic CV data.
- Documentation describes actual behavior and planned behavior separately.

## Decision Log

The entries below record current planning decisions. Both developers must confirm
them during the shared foundation review.

| Date | Decision | Reason | Approval status |
| --- | --- | --- | --- |
| 2026-08-15 | Plan Supabase Postgres and Auth for hosted persistence | One service provides database identity and authenticated user ownership | Project owner accepted; team review required |
| 2026-08-15 | Store extracted CV text, not the uploaded file | Phase 5 needs original content while avoiding permanent raw-file retention | Project owner accepted; team review required |
| 2026-08-15 | Run Phase 4 and Phase 5 in parallel after a shared foundation | Stable IDs and contracts remove the algorithm dependency between the phases | Project owner accepted; team review required |
| 2026-08-15 | Make rules mode mandatory and LLM rewriting optional | The workflow remains usable without cost while allowing improved wording | Project owner accepted; team review required |

Add future decisions using this format:

| Date | Decision | Reason | Approval status |
| --- | --- | --- | --- |
| YYYY-MM-DD | Describe the approved change and affected phase | Explain why it changed | Developer A / Developer B |
