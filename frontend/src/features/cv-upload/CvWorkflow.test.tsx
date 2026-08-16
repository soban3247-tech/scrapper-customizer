import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CvWorkflow } from "./CvWorkflow";
import { extractCv, loadSources, ProfileExtraction } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    extractCv: vi.fn(),
    loadSources: vi.fn(),
    searchJobs: vi.fn(),
  };
});

const extractCvMock = vi.mocked(extractCv);
const loadSourcesMock = vi.mocked(loadSources);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

const staleExtraction: ProfileExtraction = {
  document: { filename: "resume-a.pdf", format: "pdf", page_count: 1 },
  profile: {
    full_name: null,
    skills: ["Python"],
    job_titles: ["Stale Role"],
    years_experience: 2,
    education: [],
    domain: "Stale Domain",
    preferred_locations: [],
    remote_preference: null,
  },
  evidence: {
    skill_matches: {},
    title_matches: {},
    experience_phrases: [],
    education_lines: [],
    domain_scores: {},
  },
  suggested_search: {
    query: "Stale Role",
    skills: ["Python"],
    location: null,
    remote_only: false,
    sources: [],
  },
};

describe("CvWorkflow extraction requests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    loadSourcesMock.mockResolvedValue([]);
  });

  it("does not apply an old extraction after the selected file changes", async () => {
    const pendingExtraction = deferred<ProfileExtraction>();
    extractCvMock.mockReturnValue(pendingExtraction.promise);
    const { container } = render(<CvWorkflow />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, {
      target: { files: [new File(["a"], "resume-a.pdf", { type: "application/pdf" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: /extract skills and profile/i }));
    fireEvent.change(fileInput, {
      target: { files: [new File(["b"], "resume-b.pdf", { type: "application/pdf" })] },
    });

    await act(async () => pendingExtraction.resolve(staleExtraction));

    expect(screen.getByText("resume-b.pdf")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Stale Role")).not.toBeInTheDocument();
    expect(screen.getByText(/extract a cv to see skills/i)).toBeInTheDocument();
  });
});
