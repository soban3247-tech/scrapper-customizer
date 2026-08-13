from __future__ import annotations

import queue
import re
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from job_assistant.models import Job, SearchConfig
from job_assistant.scrapers import (
    ScraperError,
    create_default_registry,
    deduplicate_jobs,
    filter_jobs_by_date,
)

OTHER_JOB_PLATFORM_WEBPAGES = {
    "Remotive": "https://remotive.com/remote-jobs",
    "Arbeitnow": "https://www.arbeitnow.com/jobs",
    "Greenhouse job boards": "https://boards.greenhouse.io",
    "Lever job boards": "https://jobs.lever.co",
    "Ashby job boards": "https://jobs.ashbyhq.com",
    "Remote OK": "https://remoteok.com",
}

SOURCE_LABELS = {
    "hiringcafe": "HiringCafe",
    "remotive": "Remotive",
    "arbeitnow": "Arbeitnow",
    "remoteok": "Remote OK",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "ashby": "Ashby",
}

LogFn = Callable[[str], None]


def parse_user_date(value: str) -> date:
    """Parse a YYYY-MM-DD date entered by the user."""

    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            "Date must use YYYY-MM-DD format, for example 2026-07-01."
        ) from exc
    if parsed > date.today():
        raise ValueError("Start date cannot be later than today.")
    return parsed


def split_board_names(value: str) -> list[str]:
    """Split comma-, semicolon-, or newline-separated board identifiers."""

    return [
        item.strip().strip("/")
        for item in re.split(r"[\n,;]+", value)
        if item.strip()
    ]


def make_filename(query: str) -> str:
    safe_query = re.sub(r"[^a-zA-Z0-9]+", "_", query).strip("_")
    return f"{safe_query.lower()}_jobs.xlsx"


def export_to_excel(jobs: list[Job], filename: str | Path) -> Path:
    output = Path(filename)
    output.parent.mkdir(parents=True, exist_ok=True)
    dataframe = pd.DataFrame([_job_export_row(job) for job in jobs])
    dataframe.to_excel(output, index=False, engine="openpyxl")
    return output.resolve()


def _job_export_row(job: Job) -> dict[str, object]:
    return {
        "platform": job.source,
        "posted_date": job.posted_date.isoformat() if job.posted_date else "",
        "title": job.title,
        "company": job.company,
        "location": job.location or "",
        "workplace_type": job.workplace_type or "",
        "commitment": job.commitment or "",
        "salary_min": job.salary_min if job.salary_min is not None else "",
        "salary_max": job.salary_max if job.salary_max is not None else "",
        "seniority": "",
        "apply_url": str(job.apply_url),
        "source": job.source,
        "job_id": job.source_job_id or "",
    }


def run_scraper_workflow(
    *,
    query: str,
    start_date: date,
    max_pages: int,
    output_filename: str | Path,
    selected_sources: dict[str, bool],
    greenhouse_boards: list[str],
    lever_companies: list[str],
    ashby_organizations: list[str],
    log: LogFn,
) -> Path | None:
    source_ids = [
        SOURCE_LABELS[key]
        for key, enabled in selected_sources.items()
        if enabled
    ]
    config = SearchConfig(
        query=query,
        posted_after=start_date,
        max_pages=max_pages,
        sources=source_ids,
        greenhouse_boards=greenhouse_boards,
        lever_companies=lever_companies,
        ashby_organizations=ashby_organizations,
    )
    results = create_default_registry().run_selected(config)
    all_jobs: list[Job] = []
    for result in results:
        all_jobs.extend(result.jobs)
        log(f"{result.source_id}: added {len(result.jobs)} normalized jobs.")
        for issue in result.issues:
            level = "failed" if issue.fatal else "warning"
            log(f"{result.source_id} {level}: {issue.message}")

    jobs = deduplicate_jobs(all_jobs)
    if not jobs:
        log("No jobs found from the selected sources.")
        return None

    dated_jobs, missing_date_count = filter_jobs_by_date(jobs, start_date)
    log(f"Date filter: {start_date.isoformat()} to {date.today().isoformat()}")
    log(f"Jobs inside date range: {len(dated_jobs)}")
    if missing_date_count:
        log(
            f"Skipped {missing_date_count} jobs because the source did not "
            "provide a recognizable posted date."
        )
    if not dated_jobs:
        log("No jobs were found inside the selected date range.")
        return None

    saved_path = export_to_excel(dated_jobs, output_filename)
    log(f"Saved: {saved_path}")
    log(f"Completed: {len(dated_jobs)} jobs saved.")
    return saved_path


class HiringCafeScraperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Job Scraper")
        self.root.geometry("820x640")
        self.root.minsize(720, 560)

        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.query_var = tk.StringVar()
        self.start_date_var = tk.StringVar(value=datetime.now().date().isoformat())
        self.max_pages_var = tk.StringVar(value="5")
        self.output_var = tk.StringVar(value=str(Path(make_filename("jobs")).resolve()))
        self.status_var = tk.StringVar(value="Ready")
        self.source_vars = {
            "hiringcafe": tk.BooleanVar(value=True),
            "remotive": tk.BooleanVar(value=True),
            "arbeitnow": tk.BooleanVar(value=True),
            "remoteok": tk.BooleanVar(value=True),
            "greenhouse": tk.BooleanVar(value=False),
            "lever": tk.BooleanVar(value=False),
            "ashby": tk.BooleanVar(value=False),
        }
        self.greenhouse_var = tk.StringVar()
        self.lever_var = tk.StringVar()
        self.ashby_var = tk.StringVar()

        self._build_ui()
        self.root.after(100, self._drain_log_queue)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        form = ttk.Frame(self.root, padding=16)
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Job title").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Entry(form, textvariable=self.query_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(form, text="Start date").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Entry(form, textvariable=self.start_date_var, width=18).grid(
            row=1, column=1, sticky="w", pady=(10, 0)
        )
        ttk.Label(form, text="YYYY-MM-DD").grid(
            row=1, column=1, sticky="w", padx=(150, 0), pady=(10, 0)
        )

        ttk.Label(form, text="Maximum pages").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Spinbox(
            form,
            from_=1,
            to=25,
            textvariable=self.max_pages_var,
            width=8,
        ).grid(row=2, column=1, sticky="w", pady=(10, 0))

        ttk.Label(form, text="Output file").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Entry(form, textvariable=self.output_var).grid(
            row=3, column=1, sticky="ew", pady=(10, 0)
        )
        ttk.Button(form, text="Browse", command=self._browse_output).grid(
            row=3, column=2, sticky="e", padx=(10, 0), pady=(10, 0)
        )

        platforms = ttk.LabelFrame(form, text="Sources to scrape")
        platforms.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        platforms.columnconfigure(3, weight=1)

        source_order = (
            "hiringcafe",
            "remotive",
            "arbeitnow",
            "remoteok",
            "greenhouse",
            "lever",
            "ashby",
        )

        for index, source_key in enumerate(source_order):
            ttk.Checkbutton(
                platforms,
                text=SOURCE_LABELS[source_key],
                variable=self.source_vars[source_key],
            ).grid(
                row=index // 4,
                column=index % 4,
                sticky="w",
                padx=8,
                pady=4,
            )

        ttk.Label(
            platforms,
            text="Greenhouse boards",
        ).grid(row=2, column=0, sticky="w", padx=8, pady=(10, 0))
        ttk.Entry(platforms, textvariable=self.greenhouse_var).grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=8, pady=(10, 0)
        )

        ttk.Label(
            platforms,
            text="Lever companies",
        ).grid(row=3, column=0, sticky="w", padx=8, pady=(8, 0))
        ttk.Entry(platforms, textvariable=self.lever_var).grid(
            row=3, column=1, columnspan=3, sticky="ew", padx=8, pady=(8, 0)
        )

        ttk.Label(
            platforms,
            text="Ashby orgs",
        ).grid(row=4, column=0, sticky="w", padx=8, pady=(8, 8))
        ttk.Entry(platforms, textvariable=self.ashby_var).grid(
            row=4, column=1, columnspan=3, sticky="ew", padx=8, pady=(8, 8)
        )

        links_text = "Source pages: " + " | ".join(
            f"{name}: {url}" for name, url in OTHER_JOB_PLATFORM_WEBPAGES.items()
        )
        ttk.Label(platforms, text=links_text, wraplength=760).grid(
            row=5, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 8)
        )

        button_row = ttk.Frame(form)
        button_row.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        button_row.columnconfigure(1, weight=1)

        self.start_button = ttk.Button(
            button_row,
            text="Start Scraping",
            command=self._start_scraping,
        )
        self.start_button.grid(row=0, column=0, sticky="w")

        ttk.Label(button_row, textvariable=self.status_var).grid(
            row=0, column=1, sticky="e"
        )

        log_frame = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=16,
            wrap="word",
            state="disabled",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log_text.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _open_platform_links(self) -> None:
        for url in OTHER_JOB_PLATFORM_WEBPAGES.values():
            webbrowser.open_new_tab(url)

    def _browse_output(self) -> None:
        initial = Path(self.output_var.get() or ".")
        filename = filedialog.asksaveasfilename(
            title="Choose Excel output file",
            initialdir=str(initial.parent if initial.parent.exists() else Path.cwd()),
            initialfile=initial.name if initial.name else "jobs.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx"), ("All files", "*.*")],
        )
        if filename:
            self.output_var.set(filename)

    def _validate_inputs(
        self,
    ) -> tuple[str, date, int, Path, dict[str, bool], list[str], list[str], list[str]] | None:
        query = self.query_var.get().strip()
        if not query:
            messagebox.showerror("Missing job title", "Please enter a job title.")
            return None

        try:
            start_date = parse_user_date(self.start_date_var.get())
        except ValueError as exc:
            messagebox.showerror("Invalid start date", str(exc))
            return None

        try:
            max_pages = int(self.max_pages_var.get())
        except ValueError:
            messagebox.showerror("Invalid pages", "Maximum pages must be a number.")
            return None

        if max_pages < 1:
            messagebox.showerror("Invalid pages", "Maximum pages must be at least 1.")
            return None
        if max_pages > 25:
            messagebox.showerror("Invalid pages", "Maximum pages cannot exceed 25.")
            return None

        output_text = self.output_var.get().strip()
        if not output_text:
            output_text = make_filename(query)

        output_path = Path(output_text)
        if output_path.suffix.lower() != ".xlsx":
            output_path = output_path.with_suffix(".xlsx")

        selected_sources = {
            source_key: source_var.get()
            for source_key, source_var in self.source_vars.items()
        }

        greenhouse_boards = split_board_names(self.greenhouse_var.get())
        lever_companies = split_board_names(self.lever_var.get())
        ashby_organizations = split_board_names(self.ashby_var.get())

        if not any(selected_sources.values()):
            messagebox.showerror(
                "No sources selected",
                "Please select at least one job source.",
            )
            return None

        ats_requirements = (
            ("greenhouse", greenhouse_boards, "Greenhouse board names"),
            ("lever", lever_companies, "Lever company names"),
            ("ashby", ashby_organizations, "Ashby organization names"),
        )
        for source_key, values, label in ats_requirements:
            if selected_sources.get(source_key) and not values:
                messagebox.showerror(
                    "Missing company boards",
                    f"{label} are required when {SOURCE_LABELS[source_key]} is selected.",
                )
                return None

        return (
            query,
            start_date,
            max_pages,
            output_path,
            selected_sources,
            greenhouse_boards,
            lever_companies,
            ashby_organizations,
        )

    def _start_scraping(self) -> None:
        values = self._validate_inputs()
        if values is None:
            return

        (
            query,
            start_date,
            max_pages,
            output_path,
            selected_sources,
            greenhouse_boards,
            lever_companies,
            ashby_organizations,
        ) = values
        self.output_var.set(str(output_path))
        self._clear_log()
        self._set_running(True)
        self._log("Starting scraper...")

        self.worker = threading.Thread(
            target=self._worker_run,
            args=(
                query,
                start_date,
                max_pages,
                output_path,
                selected_sources,
                greenhouse_boards,
                lever_companies,
                ashby_organizations,
            ),
            daemon=True,
        )
        self.worker.start()

    def _worker_run(
        self,
        query: str,
        start_date: date,
        max_pages: int,
        output_path: Path,
        selected_sources: dict[str, bool],
        greenhouse_boards: list[str],
        lever_companies: list[str],
        ashby_organizations: list[str],
    ) -> None:
        try:
            saved_path = run_scraper_workflow(
                query=query,
                start_date=start_date,
                max_pages=max_pages,
                output_filename=output_path,
                selected_sources=selected_sources,
                greenhouse_boards=greenhouse_boards,
                lever_companies=lever_companies,
                ashby_organizations=ashby_organizations,
                log=self._thread_log,
            )

            if saved_path is None:
                self.log_queue.put(("done", "Finished with no Excel file created."))
            else:
                self.log_queue.put(("done", f"Finished. Saved file: {saved_path}"))

        except ScraperError as exc:
            self.log_queue.put(("error", f"SCRAPER ERROR\n{'=' * 60}\n{exc}"))
        except Exception as exc:
            self.log_queue.put(
                ("error", f"Unexpected error: {type(exc).__name__}: {exc}")
            )

    def _thread_log(self, message: str) -> None:
        self.log_queue.put(("log", message))

    def _drain_log_queue(self) -> None:
        try:
            while True:
                kind, message = self.log_queue.get_nowait()

                if kind == "log":
                    self._log(message)
                elif kind == "done":
                    self._log(message)
                    self._set_running(False)
                    messagebox.showinfo("Scraping complete", message)
                elif kind == "error":
                    self._log(message)
                    self._set_running(False)
                    messagebox.showerror("Scraping failed", message)

        except queue.Empty:
            pass

        self.root.after(100, self._drain_log_queue)

    def _set_running(self, running: bool) -> None:
        if running:
            self.start_button.configure(state="disabled")
            self.status_var.set("Running...")
        else:
            self.start_button.configure(state="normal")
            self.status_var.set("Ready")

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


def main() -> int:
    root = tk.Tk()
    HiringCafeScraperApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
