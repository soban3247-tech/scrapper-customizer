export type Profile = {
  full_name: string | null;
  skills: string[];
  job_titles: string[];
  years_experience: number | null;
  education: string[];
  domain: string | null;
  preferred_locations: string[];
  remote_preference: boolean | null;
};

export type SuggestedSearch = {
  query: string;
  skills: string[];
  location: string | null;
  remote_only: boolean;
  sources: string[];
};

export type ProfileExtraction = {
  document: { filename: string; format: string; page_count: number | null };
  profile: Profile;
  evidence: {
    skill_matches: Record<string, string[]>;
    title_matches: Record<string, string[]>;
    experience_phrases: string[];
    education_lines: string[];
    domain_scores: Record<string, number>;
  };
  suggested_search: SuggestedSearch;
};

export type ConfigField = {
  key: string;
  label: string;
  kind: "text" | "secret" | "string_list" | "boolean" | "integer";
  required: boolean;
  help_text: string | null;
};

export type SourceDescriptor = {
  source_id: string;
  display_name: string;
  capabilities: { configuration_fields: ConfigField[] };
};

export type Job = {
  source: string;
  source_job_id: string | null;
  title: string;
  company: string;
  location: string | null;
  workplace_type: string | null;
  posted_date: string | null;
  apply_url: string;
  tags: string[];
};

export type JobSearchResponse = {
  jobs: Job[];
  issues: Array<{ source_id: string; message: string; fatal: boolean }>;
  missing_date_count: number;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function formatApiErrorDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (!Array.isArray(detail)) return null;

  const messages = detail.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const entry = item as { loc?: unknown; msg?: unknown };
    if (typeof entry.msg !== "string") return [];
    const location = Array.isArray(entry.loc)
      ? entry.loc.filter((part) => part !== "body").map(String).join(" → ")
      : "";
    return [location ? `${location}: ${entry.msg}` : entry.msg];
  });

  return messages.length > 0 ? messages.join("; ") : null;
}

async function readResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(
      formatApiErrorDetail(body?.detail) ?? `Request failed with status ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}

export async function extractCv(file: File): Promise<ProfileExtraction> {
  const formData = new FormData();
  formData.append("file", file);
  return readResponse<ProfileExtraction>(
    await fetch(`${API_URL}/profiles/extract`, { method: "POST", body: formData }),
  );
}

export async function loadSources(): Promise<SourceDescriptor[]> {
  return readResponse<SourceDescriptor[]>(await fetch(`${API_URL}/jobs/sources`));
}

export async function searchJobs(payload: Record<string, unknown>): Promise<JobSearchResponse> {
  return readResponse<JobSearchResponse>(
    await fetch(`${API_URL}/jobs/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}
