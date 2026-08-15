# Test fixtures

Store only synthetic or fully anonymized CVs and saved job-source responses in
this directory. Never commit a real user's CV, contact details, credentials, or
live API tokens.

## Synthetic CV fixtures

The `cvs/` directory contains two entirely fictional one-page CVs used by the
reader-to-profile integration tests:

- `synthetic_backend_cv.pdf` exercises PDF text reading and software profile
  extraction.
- `synthetic_data_cv.docx` exercises DOCX text reading and data profile
  extraction.

Regenerate both fixtures after installing the project requirements:

```powershell
uv run python backend/tests/fixtures/generate_sample_cvs.py
```

The names, employers, universities, and work histories in these files are test
data and do not describe real people.
