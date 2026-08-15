"use client";

import {
  AlertCircle,
  ArrowUpRight,
  BriefcaseBusiness,
  Check,
  FileText,
  LoaderCircle,
  Search,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { ChangeEvent, DragEvent, useMemo, useRef, useState } from "react";

import {
  extractCv,
  JobSearchResponse,
  loadSources,
  ProfileExtraction,
  searchJobs,
  SourceDescriptor,
} from "@/lib/api";

type SearchDraft = {
  query: string;
  skills: string[];
  location: string;
  remoteOnly: boolean;
  postedAfter: string;
  maxPages: number;
  sources: string[];
};

const today = new Date();
const initialDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 14)
  .toISOString()
  .slice(0, 10);

export function CvWorkflow() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [extraction, setExtraction] = useState<ProfileExtraction | null>(null);
  const [sources, setSources] = useState<SourceDescriptor[]>([]);
  const [sourceOptions, setSourceOptions] = useState<Record<string, Record<string, string>>>({});
  const [draft, setDraft] = useState<SearchDraft | null>(null);
  const [skillInput, setSkillInput] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<JobSearchResponse | null>(null);

  const selectedDescriptors = useMemo(
    () => sources.filter((source) => draft?.sources.includes(source.source_id)),
    [draft?.sources, sources],
  );

  function acceptFile(nextFile: File | undefined) {
    if (!nextFile) return;
    const extension = nextFile.name.split(".").pop()?.toLowerCase();
    if (extension !== "pdf" && extension !== "docx") {
      setError("Choose a PDF or DOCX CV.");
      return;
    }
    setFile(nextFile);
    setExtraction(null);
    setDraft(null);
    setResults(null);
    setError("");
  }

  async function handleExtract() {
    if (!file) return;
    setIsExtracting(true);
    setError("");
    try {
      const [profileResult, availableSources] = await Promise.all([
        extractCv(file),
        loadSources(),
      ]);
      setExtraction(profileResult);
      setSources(availableSources);
      setDraft({
        query: profileResult.suggested_search.query,
        skills: profileResult.suggested_search.skills,
        location: profileResult.suggested_search.location ?? "",
        remoteOnly: profileResult.suggested_search.remote_only,
        postedAfter: initialDate,
        maxPages: 3,
        sources: profileResult.suggested_search.sources,
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "CV extraction failed.");
    } finally {
      setIsExtracting(false);
    }
  }

  function toggleSource(sourceId: string) {
    if (!draft) return;
    const selected = draft.sources.includes(sourceId);
    setDraft({
      ...draft,
      sources: selected
        ? draft.sources.filter((source) => source !== sourceId)
        : [...draft.sources, sourceId],
    });
  }

  function addSkill() {
    if (!draft) return;
    const skill = skillInput.trim();
    if (skill && !draft.skills.some((item) => item.toLowerCase() === skill.toLowerCase())) {
      setDraft({ ...draft, skills: [...draft.skills, skill] });
    }
    setSkillInput("");
  }

  async function handleSearch() {
    if (!draft || !draft.query.trim() || draft.sources.length === 0) return;
    setIsSearching(true);
    setError("");
    setResults(null);
    const options = Object.fromEntries(
      Object.entries(sourceOptions).map(([source, values]) => [
        source,
        Object.fromEntries(
          Object.entries(values).map(([key, value]) => [
            key,
            value.includes(",") ? value.split(",").map((item) => item.trim()).filter(Boolean) : value,
          ]),
        ),
      ]),
    );
    try {
      setResults(
        await searchJobs({
          query: draft.query,
          skills: draft.skills,
          location: draft.location || null,
          remote_only: draft.remoteOnly,
          posted_after: draft.postedAfter || null,
          max_pages: draft.maxPages,
          sources: draft.sources,
          source_options: options,
        }),
      );
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Job search failed.");
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand"><BriefcaseBusiness size={21} /><span>JobFit Workspace</span></div>
        <div className="api-state"><span className="status-dot" /> FastAPI connected locally</div>
      </header>

      <div className="page-shell">
        <section className="page-heading">
          <div>
            <p className="eyebrow">CV-driven job discovery</p>
            <h1>Build your search profile</h1>
            <p>Upload a CV, verify what was detected, then choose exactly what the scrapers use.</p>
          </div>
          <ol className="steps" aria-label="Workflow progress">
            <li className="active"><span>1</span> Upload</li>
            <li className={extraction ? "active" : ""}><span>2</span> Review</li>
            <li className={results ? "active" : ""}><span>3</span> Results</li>
          </ol>
        </section>

        {error && <div className="alert"><AlertCircle size={18} /><span>{error}</span></div>}

        <section className="workspace-grid">
          <div className="panel upload-panel">
            <div className="panel-title"><FileText size={19} /><div><h2>CV document</h2><p>PDF or DOCX, up to 10 MB</p></div></div>
            <div
              className={`dropzone ${isDragging ? "dragging" : ""}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(event: DragEvent) => { event.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(event: DragEvent) => {
                event.preventDefault();
                setIsDragging(false);
                acceptFile(event.dataTransfer.files[0]);
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => event.key === "Enter" && inputRef.current?.click()}
            >
              <UploadCloud size={28} />
              <strong>{file ? file.name : "Drop your CV here"}</strong>
              <span>{file ? `${(file.size / 1024).toFixed(0)} KB selected` : "or click to choose a file"}</span>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.docx"
                hidden
                onChange={(event: ChangeEvent<HTMLInputElement>) => acceptFile(event.target.files?.[0])}
              />
            </div>
            <button className="primary-button" disabled={!file || isExtracting} onClick={handleExtract}>
              {isExtracting ? <LoaderCircle className="spin" size={18} /> : <Sparkles size={18} />}
              {isExtracting ? "Extracting profile..." : "Extract skills and profile"}
            </button>
            <div className="privacy-note"><Check size={15} /> Your CV is processed in memory and is not saved by this step.</div>
          </div>

          <div className="panel profile-panel">
            <div className="panel-title"><Sparkles size={19} /><div><h2>Detected profile</h2><p>Review before searching</p></div></div>
            {!extraction || !draft ? (
              <div className="empty-state"><FileText size={28} /><p>Extract a CV to see skills, titles, domain, and experience.</p></div>
            ) : (
              <div className="profile-content">
                <div className="summary-grid">
                  <label><span>Search title</span><input value={draft.query} onChange={(e) => setDraft({ ...draft, query: e.target.value })} /></label>
                  <label><span>Career domain</span><input value={extraction.profile.domain ?? "Not detected"} readOnly /></label>
                  <label><span>Experience</span><input value={extraction.profile.years_experience == null ? "Not detected" : `${extraction.profile.years_experience} years`} readOnly /></label>
                  <label><span>Location</span><input placeholder="Any location" value={draft.location} onChange={(e) => setDraft({ ...draft, location: e.target.value })} /></label>
                </div>
                <div className="field-block">
                  <span className="field-label">Skills saved for filtering and ranking</span>
                  <div className="skill-list">
                    {draft.skills.map((skill) => (
                      <button key={skill} className="skill-chip" onClick={() => setDraft({ ...draft, skills: draft.skills.filter((item) => item !== skill) })} title={`Remove ${skill}`}>
                        {skill}<X size={13} />
                      </button>
                    ))}
                  </div>
                  <div className="inline-input">
                    <input placeholder="Add a missing skill" value={skillInput} onChange={(e) => setSkillInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSkill(); } }} />
                    <button onClick={addSkill}>Add</button>
                  </div>
                </div>
                {extraction.profile.education.length > 0 && <p className="evidence-line"><strong>Education:</strong> {extraction.profile.education.join("; ")}</p>}
              </div>
            )}
          </div>
        </section>

        {draft && (
          <section className="panel search-panel">
            <div className="panel-title"><Search size={19} /><div><h2>Scraper configuration</h2><p>The search title and source settings run now; skill ranking is Phase 4</p></div></div>
            <div className="search-layout">
              <div>
                <span className="field-label">Job sources</span>
                <div className="source-grid">
                  {sources.map((source) => {
                    const selected = draft.sources.includes(source.source_id);
                    return <button key={source.source_id} className={`source-option ${selected ? "selected" : ""}`} onClick={() => toggleSource(source.source_id)}><span className="checkbox">{selected && <Check size={14} />}</span>{source.display_name}</button>;
                  })}
                </div>
                {selectedDescriptors.flatMap((source) => source.capabilities.configuration_fields.map((field) => (
                  <label className="source-field" key={`${source.source_id}-${field.key}`}>
                    <span>{source.display_name}: {field.label}{field.required ? " *" : ""}</span>
                    <input
                      type={field.kind === "secret" ? "password" : field.kind === "integer" ? "number" : "text"}
                      placeholder={field.help_text ?? undefined}
                      value={sourceOptions[source.source_id]?.[field.key] ?? ""}
                      onChange={(e) => setSourceOptions({ ...sourceOptions, [source.source_id]: { ...sourceOptions[source.source_id], [field.key]: e.target.value } })}
                    />
                  </label>
                )))}
              </div>
              <div className="search-controls">
                <label><span>Posted after</span><input type="date" value={draft.postedAfter} onChange={(e) => setDraft({ ...draft, postedAfter: e.target.value })} /></label>
                <label><span>Maximum pages</span><input type="number" min={1} max={25} value={draft.maxPages} onChange={(e) => setDraft({ ...draft, maxPages: Number(e.target.value) })} /></label>
                <label className="toggle-row"><input type="checkbox" checked={draft.remoteOnly} onChange={(e) => setDraft({ ...draft, remoteOnly: e.target.checked })} /><span>Remote roles only</span></label>
                <button className="primary-button" disabled={isSearching || !draft.query || draft.sources.length === 0} onClick={handleSearch}>
                  {isSearching ? <LoaderCircle className="spin" size={18} /> : <Search size={18} />}
                  {isSearching ? "Searching sources..." : "Search selected sources"}
                </button>
              </div>
            </div>
          </section>
        )}

        {results && <ResultsSection results={results} />}
      </div>
    </main>
  );
}

function ResultsSection({ results }: { results: JobSearchResponse }) {
  return (
    <section className="results-section">
      <div className="results-heading"><div><p className="eyebrow">Normalized results</p><h2>{results.jobs.length} jobs found</h2></div><span>{results.issues.length} source notices</span></div>
      {results.issues.map((issue) => <div className="notice" key={`${issue.source_id}-${issue.message}`}><AlertCircle size={16} /><strong>{issue.source_id}:</strong> {issue.message}</div>)}
      {results.jobs.length === 0 ? <div className="panel empty-results">No dated jobs matched this search. Adjust the date, title, or sources.</div> : (
        <div className="job-list">
          {results.jobs.map((job) => (
            <article className="job-row" key={`${job.source}-${job.source_job_id ?? job.apply_url}`}>
              <div className="company-mark">{job.company.slice(0, 2).toUpperCase()}</div>
              <div className="job-main"><h3>{job.title}</h3><p>{job.company} · {job.location || "Location not provided"}</p><div className="job-meta"><span>{job.source}</span>{job.posted_date && <span>{job.posted_date}</span>}{job.workplace_type && <span>{job.workplace_type}</span>}</div></div>
              <a className="icon-link" href={job.apply_url} target="_blank" rel="noreferrer" title="Open job posting"><ArrowUpRight size={19} /></a>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
