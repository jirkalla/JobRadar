"""JobRadar CLI — job application tracker for Jiri Vosta.

Entry point for all CLI commands. This file orchestrates — it never
contains business logic. All real work is done in src/ modules.
"""

import argparse
import json
import shutil
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from src.pdf_writer import cv_md_to_pdf, cover_letter_md_to_pdf
from src._version import __version__


VERSION = f"job-tracker v{__version__}"


def load_profile() -> dict:
    """Load and return config/profile.yaml as a dict.

    Raises:
        FileNotFoundError: If config/profile.yaml does not exist.
    """
    profile_path = Path("config/profile.yaml")
    if not profile_path.exists():
        raise FileNotFoundError(
            "config/profile.yaml not found. Run python setup.py first."
        )
    import yaml
    return yaml.safe_load(profile_path.read_text(encoding="utf-8"))


def _parse_json_field(value) -> list:
    """Safely parse a DB field that may be None, a list, or a JSON string."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []


def _show_filter_table(stubs: list, console: object) -> None:
    """Display all job stubs as a numbered Rich table for quick review."""
    from rich.table import Table
    table = Table(title=f"Found {len(stubs)} jobs — mark obvious skips before scoring")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", max_width=45)
    table.add_column("Company", max_width=22)
    table.add_column("Location", max_width=22)
    table.add_column("Date", width=12)
    for i, s in enumerate(stubs, 1):
        table.add_row(str(i), s.title[:45], s.company[:22], s.location[:22], s.date_seen)
    console.print(table)


def _quick_filter(stubs: list, console: object) -> tuple[list, list]:
    """Prompt keep/skip/reject per job. Returns (kept, rejected) lists."""
    console.print("\n[dim]ENTER = keep  |  s = skip  |  r = reject[/dim]\n")
    kept, rejected = [], []
    total = len(stubs)
    for i, stub in enumerate(stubs, 1):
        label = f"[{i:2}/{total}] {stub.title[:44]:<44} | {stub.company[:20]:<20}"
        choice = input(f"{label}  > ").strip().lower()
        if choice == "r":
            rejected.append(stub)
        elif choice == "s":
            pass  # skip — not saved to DB
        else:
            kept.append(stub)
    return kept, rejected


def _run_scoring(
    kept: list,
    profile: dict,
    client: object,
    template: str,
    filename: str,
    console: object,
) -> list:
    """Score all kept stubs with a progress spinner. Returns list of (stub, result)."""
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from src.scorer import score_job
    results = []
    n = len(kept)
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
        task_id = prog.add_task("Starting...", total=n)
        for i, stub in enumerate(kept, 1):
            prog.update(task_id, description=f"[{i}/{n}] Scoring: {stub.title[:40]} — {stub.company}")
            result = score_job(stub, profile, client, template)
            result["source_eml"] = filename
            results.append((stub, result))
            prog.advance(task_id)
    return results


def _show_results_table(results: list, console: object) -> None:
    """Display scored results as a Rich table sorted by score descending."""
    from rich.table import Table
    sorted_r = sorted(results, key=lambda x: x[1].get("score", 0), reverse=True)
    table = Table(title="Scoring Results")
    table.add_column("Score", width=6, justify="center")
    table.add_column("Title", max_width=40)
    table.add_column("Company", max_width=20)
    table.add_column("Location", max_width=24)
    table.add_column("Remote", width=8)
    table.add_column("Salary", width=8)
    table.add_column("Reason", max_width=35)
    for _, result in sorted_r:
        score = result.get("score", 0)
        if score >= 7:
            score_cell = f"[green]{score}[/green]"
        elif score >= 5:
            score_cell = f"[yellow]{score}[/yellow]"
        else:
            score_cell = f"[red]{score}[/red]"
        loc = result.get("location") or ""
        if not result.get("location_ok", True):
            loc = f"{loc} [red]NO-LOC[/red]"
        table.add_row(
            score_cell,
            (result.get("role_title") or "")[:40],
            (result.get("company") or "")[:20],
            loc[:24],
            (result.get("remote_type") or "")[:8],
            str(result.get("salary") or "")[:8],
            (result.get("score_reason") or "")[:35],
        )
    console.print(table)


def _process_single_eml(
    eml_path: Path,
    profile: dict,
    client: object,
    prompt_template: str,
    console: object,
) -> None:
    """Parse, filter, score, and store one EML file."""
    from src.parser import parse_eml
    from src.db import insert_job, job_exists_for_eml, find_similar_job
    filename = eml_path.name
    if job_exists_for_eml(filename):
        console.print(f"Already processed: {filename}")
        return
    stubs = parse_eml(eml_path)
    if not stubs:
        console.print(f"[yellow]No jobs found in {filename}[/yellow]")
        return
    _show_filter_table(stubs, console)
    kept, rejected = _quick_filter(stubs, console)

    # Duplicate check — BEFORE scoring
    deduped = []
    for stub in kept:
        existing = find_similar_job(stub.company, stub.title)
        if existing:
            console.print(f"\n[yellow]WARNING: Similar job already in DB:[/yellow]")
            console.print(f"  {existing['role_title']} at {existing['company']}")
            console.print(f"  Status: {existing['status']}  Score: {existing['score']}/10")
            choice = input("  [S]kip / [K]eep as new / [V]iew full details: ").strip().lower()
            if choice == "v":
                console.print(f"  Score reason: {existing['score_reason']}")
                choice = input("  [S]kip / [K]eep as new: ").strip().lower()
            if choice == "s":
                continue
        deduped.append(stub)
    kept = deduped

    console.print(f"\nKeeping [bold]{len(kept)}[/bold] jobs. Fetching and scoring... (this takes ~2 min)")
    results = _run_scoring(kept, profile, client, prompt_template, filename, console)
    n_saved = n_failed = 0
    for stub, result in results:
        try:
            insert_job(result)
            n_saved += 1
        except Exception as exc:
            console.print(f"[red]DB error for {stub.title}: {exc}[/red]")
            n_failed += 1
    _show_results_table(results, console)
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(eml_path), processed_dir / filename)
    n_skipped = len(stubs) - len(kept) - len(rejected)
    console.print(f"\n[bold]Summary:[/bold] {n_saved} scored, {n_skipped} skipped, {len(rejected)} rejected, {n_failed} failed")
    console.print(f"[green]Moved {filename} to data/processed/[/green]")


def cmd_process(args: argparse.Namespace) -> None:
    """Parse inbox emails, quick-filter, score with AI, and write to DB."""
    from rich.console import Console
    from src.parser import scan_inbox
    from src.db import init_db
    from src.ai_client import get_client
    console = Console()
    try:
        profile = load_profile()
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    init_db()
    try:
        client = get_client(profile)
    except EnvironmentError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    prompt_path = Path("config/prompts/score.txt")
    if not prompt_path.exists():
        console.print("[red]config/prompts/score.txt not found.[/red]")
        return
    prompt_template = prompt_path.read_text(encoding="utf-8")
    eml_files = scan_inbox(Path("inbox"))
    if not eml_files:
        console.print("No .eml files found in inbox/")
        return
    for eml_path in eml_files:
        _process_single_eml(eml_path, profile, client, prompt_template, console)


def _show_review_table(jobs: list, console: object) -> None:
    """Display jobs as a numbered Rich table for review, sorted by score descending."""
    from rich.table import Table
    table = Table(title=f"{len(jobs)} jobs to review")
    table.add_column("#", style="dim", width=4)
    table.add_column("Score", width=6, justify="center")
    table.add_column("Title", max_width=40)
    table.add_column("Company", max_width=20)
    table.add_column("Location", max_width=22)
    table.add_column("Remote", width=8)
    table.add_column("Salary", width=8)
    table.add_column("Status", width=10)
    for i, job in enumerate(jobs, 1):
        score = job.get("score", 0) or 0
        if score >= 7:
            score_cell = f"[green]{score}[/green]"
        elif score >= 5:
            score_cell = f"[yellow]{score}[/yellow]"
        else:
            score_cell = f"[red]{score}[/red]"
        loc = job.get("location") or ""
        if not job.get("location_ok", True):
            loc = f"{loc} [red]NO-LOC[/red]"
        table.add_row(
            str(i),
            score_cell,
            (job.get("role_title") or "")[:40],
            (job.get("company") or "")[:20],
            loc[:22],
            (job.get("remote_type") or "")[:8],
            str(job.get("salary") or "")[:8],
            job.get("status") or "",
        )
    console.print(table)


def cmd_review(args: argparse.Namespace) -> None:
    """Review scored jobs — approve, reject, skip, or add notes."""
    from rich.console import Console
    from src.db import init_db, get_jobs, update_job_status
    console = Console()
    try:
        profile = load_profile()
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    init_db()
    min_score = args.min if args.min is not None else profile.get("preferences", {}).get("min_score_to_show", 0)

    def fetch_jobs() -> list:
        jobs = get_jobs(min_score=min_score)
        if not args.all:
            jobs = [j for j in jobs if j.get("status") in ("new", "reviewed")]
        return jobs

    jobs = fetch_jobs()
    if not jobs:
        console.print("No jobs to review.")
        return

    while True:
        jobs = fetch_jobs()
        if not jobs:
            console.print("[green]All done — no more jobs to review.[/green]")
            break
        _show_review_table(jobs, console)
        raw = input("\nEnter job number to act on (or 'q' to quit): ").strip().lower()
        if raw == "q":
            break
        if not raw.isdigit() or not (1 <= int(raw) <= len(jobs)):
            console.print("[yellow]Invalid number — try again.[/yellow]")
            continue
        job = jobs[int(raw) - 1]
        job_id = job["id"]
        console.print(f"\n[bold]{job.get('role_title')}[/bold] — {job.get('company')}")
        action = input("[A]pprove / [R]eject / [S]kip / [N]otes: ").strip().lower()
        if action == "a":
            update_job_status(job_id, "approved")
            console.print("[green]Approved.[/green]")
        elif action == "r":
            update_job_status(job_id, "rejected")
            console.print("[red]Rejected.[/red]")
        elif action == "n":
            notes = input("Notes: ").strip()
            update_job_status(job_id, job.get("status", "reviewed"), notes=notes)
            console.print("[dim]Notes saved.[/dim]")
        elif action == "s":
            pass
        else:
            console.print("[yellow]Unknown action — skipping.[/yellow]")


def cmd_fetch(args: argparse.Namespace) -> None:
    """Download new Infoagent digest emails from Forpsi IMAP to inbox/."""
    import os
    from rich.console import Console
    from src.fetcher import fetch_digests

    console = Console()
    try:
        profile = load_profile()
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return

    fetch_cfg = profile.get("fetch", {})
    sender = fetch_cfg.get("sender", "info@anzeigendaten.de")
    subject = fetch_cfg.get("subject") or None
    filename_prefix = fetch_cfg.get("filename_prefix", "Suche_Infoagent")
    since = args.since or None
    until = args.until or None
    on_date = args.date or None

    if until and not since:
        console.print("[red]Error: --until requires --since[/red]")
        console.print("Example: python main.py fetch --since 2026-02-16 --until 2026-02-22")
        return

    try:
        count, files = fetch_digests(
            inbox_dir=Path("inbox"),
            processed_dir=Path("data/processed"),
            env=os.environ,
            sender=sender,
            subject=subject,
            since=since,
            until=until,
            on_date=on_date,
            filename_prefix=filename_prefix,
        )
    except EnvironmentError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    except ConnectionError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(
            "[yellow]Tip: place .eml files in inbox/ manually and run: python main.py process[/yellow]"
        )
        return

    if count == 0:
        console.print("[yellow]No new job digests found.[/yellow]")
        console.print(f"Tip: check that Forpsi is receiving emails from {sender}")
    else:
        console.print(f"[green]Downloaded {count} digest(s):[/green]")
        for f in files:
            console.print(f"  {f}")
        console.print("\nRun: python main.py process")


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate a tailored CV and cover letter for an approved job."""
    import json
    from datetime import datetime, timezone
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    from src.db import (
        init_db, get_jobs, get_job,
        save_document, rate_document,
        log_action, update_job_status,
    )
    from src.ai_client import get_client
    from src import generator
    from src.generator import _slugify

    console = Console()
    try:
        profile = load_profile()
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    init_db()

    # Step 1 — Select job
    if args.job_id:
        job = get_job(args.job_id)
        if job is None:
            console.print(f"[red]Job not found: {args.job_id}[/red]")
            return
        if job['status'] != 'approved':
            console.print(f"[red]Job status is '{job['status']}' — only approved jobs can be generated.[/red]")
            return
    else:
        jobs = get_jobs(status='approved')
        if not jobs:
            console.print("[yellow]No approved jobs. Run: python main.py review[/yellow]")
            return
        from rich.table import Table
        table = Table(title=f"{len(jobs)} approved jobs")
        table.add_column("#", style="dim", width=4)
        table.add_column("Company", max_width=22)
        table.add_column("Role", max_width=40)
        table.add_column("Score", width=6, justify="center")
        table.add_column("Location", max_width=22)
        table.add_column("Created", width=12)
        for i, j in enumerate(jobs, 1):
            score = j.get("score", 0) or 0
            if score >= 7:
                score_cell = f"[green]{score}[/green]"
            elif score >= 5:
                score_cell = f"[yellow]{score}[/yellow]"
            else:
                score_cell = f"[red]{score}[/red]"
            table.add_row(
                str(i),
                (j.get("company") or "")[:22],
                (j.get("role_title") or "")[:40],
                score_cell,
                (j.get("location") or "")[:22],
                (j.get("created_at") or "")[:10],
            )
        console.print(table)
        raw = input("Enter job number to generate documents (or 'q' to quit): ").strip().lower()
        if raw == 'q':
            return
        if not raw.isdigit() or not (1 <= int(raw) <= len(jobs)):
            raw = input("Invalid. Enter job number (or 'q'): ").strip().lower()
            if raw == 'q' or not raw.isdigit() or not (1 <= int(raw) <= len(jobs)):
                return
        job = get_job(jobs[int(raw) - 1]['id'])

    # Step 2 — Validate jd_text
    if not job.get('jd_text'):
        console.print("[red]No job description stored for this job. Cannot generate.[/red]")
        console.print("Tip: this job may have been entered via backfill. Run fetch+process for a scored job.")
        return

    # Step 3 — Generate cover letter
    try:
        client = get_client(profile)
    except EnvironmentError as exc:
        console.print(f"[red]{exc}[/red]")
        return

    cl_text = None
    banned_error = None
    for attempt in range(1, 4):
        with console.status(f"Generating cover letter (attempt {attempt}/3)..."):
            try:
                cl_text = generator.generate_cover_letter(
                    client, profile, job['jd_text'], job.get('language', 'en')
                )
                break
            except ValueError as exc:
                banned_error = str(exc)
        # spinner has stopped — safe to print and accept input
        if cl_text is None:
            console.print(f"[red]{banned_error}[/red]")
            if attempt == 3:
                console.print("[red]Could not produce a clean letter after 3 attempts. Quit and edit manually.[/red]")
                return
            choice = input("[Y] Try again / [Q] Quit: ").strip().lower()
            if choice != 'y':
                return

    console.print(Panel(cl_text, title=f"Cover Letter — {job['company']}", expand=False))

    # Step 4 — Generate CV changes
    cv_changes = None
    with console.status("Generating CV tailoring suggestions..."):
        try:
            cv_changes = generator.generate_cv_changes(client, profile, job['jd_text'])
        except FileNotFoundError:
            console.print("[red]examples/cv_base.md not found — skipping CV tailoring.[/red]")
        except ValueError as exc:
            console.print(f"[red]AI returned invalid response for CV changes. Skipping CV tailoring.[/red]")
            console.print(f"[dim]{exc}[/dim]")

    if cv_changes is not None:
        lines = [
            f"Summary:   {cv_changes['profile_summary']}",
            f"Highlight: {', '.join(cv_changes['skills_to_highlight'])}",
            f"Remove:    {', '.join(cv_changes['skills_to_remove'])}",
            f"Why:       {cv_changes['changes_explained']}",
            "",
            "Note: skills changes are recommendations — apply them manually to the saved CV.",
        ]
        console.print(Panel('\n'.join(lines), title=f"Proposed CV Changes — {job['company']}", expand=False))

    # Step 5 — Confirm before saving
    console.print("\nReview the output above.")
    if cv_changes is not None:
        prompt = "[S] Save both / [C] Cover letter only / [Q] Quit without saving: "
        valid = {'s', 'c', 'q'}
    else:
        prompt = "[C] Save cover letter / [Q] Quit without saving: "
        valid = {'c', 'q'}

    while True:
        save_choice = input(prompt).strip().lower()
        if save_choice in valid:
            break
        console.print(f"[yellow]Please enter one of: {', '.join(sorted(valid)).upper()}[/yellow]")

    if save_choice == 'q':
        console.print("Nothing saved.")
        return

    # Step 6 — Overwrite check and save
    today_date = datetime.now(timezone.utc).strftime('%Y%m%d')
    date_input = input(f"Output date (YYYYMMDD) [{today_date}]: ").strip()
    applied_date = date_input if (date_input and date_input.isdigit() and len(date_input) == 8) else today_date
    output_dir = generator.make_output_dir(job['company'], job['role_title'], applied_date)
    cl_doc_id: int | None = None   # must be initialised here — Step 7 checks it

    if output_dir.exists():
        console.print(f"[yellow]Output folder already exists: {output_dir}[/yellow]")
        ow = input("[O] Overwrite / [V] Save as new version / [Q] Quit: ").strip().lower()
        if ow == 'q':
            console.print("Nothing saved.")
            return
        elif ow == 'v':
            base = str(output_dir)
            for n in range(2, 10):
                candidate = Path(f"{base}_v{n}")
                if not candidate.exists():
                    output_dir = candidate
                    break
            else:
                console.print("[red]Too many versions already exist. Clean up output/ manually.[/red]")
                return
        # 'o' → proceed with existing output_dir, files will be overwritten

    output_dir.mkdir(parents=True, exist_ok=True)
    company_slug = _slugify(job['company'])

    # Always write these two files
    (output_dir / 'jd_snapshot.txt').write_text(job['jd_text'] or '', encoding='utf-8')

    score_data = {
        'job_id':         job['id'],
        'score':          job['score'],
        'score_reason':   job['score_reason'],
        'strong_matches': _parse_json_field(job.get('strong_matches')),
        'concerns':       _parse_json_field(job.get('concerns')),
        'tech_stack':     _parse_json_field(job.get('tech_stack')),
        'salary':         job.get('salary'),
        'generated_at':   datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / 'score.json').write_text(
        json.dumps(score_data, indent=2, ensure_ascii=False), encoding='utf-8'
    )

    # Save cover letter (save_choice 's' or 'c')
    cl_md_path   = output_dir / f"cl_{applied_date}_{company_slug}.md"
    cl_pdf_path  = output_dir / f"cl_{applied_date}_{company_slug}.pdf"
    cl_body_path = output_dir / f"cl_{applied_date}_{company_slug}_body.md"
    generator.write_cover_letter_md(
        cl_text, cl_md_path, cl_body_path,
        profile, job['company'], applied_date, job.get('language', 'en'),
    )
    cover_letter_md_to_pdf(cl_md_path, cl_pdf_path)
    cl_doc_id = save_document(job['id'], 'cover_letter', str(cl_body_path))
    console.print(f"[green]Cover letter saved: {cl_md_path}[/green]")
    console.print(f"[green]Cover letter PDF: {cl_pdf_path}[/green]")

    # Save CV (save_choice 's' only, and cv_changes is not None)
    if save_choice == 's' and cv_changes is not None:
        cv_base = Path('examples/cv_base.md')
        if not cv_base.exists():
            console.print("[red]examples/cv_base.md not found — skipping CV save.[/red]")
        else:
            cv_md_path  = output_dir / f"cv_{applied_date}_{company_slug}.md"
            cv_pdf_path = output_dir / f"cv_{applied_date}_{company_slug}.pdf"
            generator.apply_cv_changes(cv_base, cv_changes, cv_md_path)
            cv_md_to_pdf(cv_md_path, cv_pdf_path)
            save_document(job['id'], 'cv', str(cv_md_path))
            console.print(f"[green]CV saved: {cv_md_path}[/green]")
            console.print(f"[green]CV PDF: {cv_pdf_path}[/green]")

    log_action(job['id'], 'generated', detail=str(output_dir))

    # Step 7 — Rate the cover letter
    if cl_doc_id is not None:
        rating_input = input("Rate this cover letter 1-5 (or press Enter to skip): ").strip()
        if rating_input.isdigit() and 1 <= int(rating_input) <= 5:
            rate_document(cl_doc_id, int(rating_input))
            if int(rating_input) >= 4:
                console.print("[green]Letter added to example pool for future generations.[/green]")
            else:
                console.print("Rating saved.")
        else:
            console.print("Rating skipped.")

    # Step 8 — Update job status
    apply_choice = input("Mark this job as applied? [Y/N]: ").strip().lower()
    if apply_choice == 'y':
        update_job_status(job['id'], 'applied', applied_at=applied_date)
        console.print("[green]Job status updated to 'applied'.[/green]")
    else:
        console.print("Status unchanged (still 'approved').")


def cmd_reset(args: argparse.Namespace) -> None:
    """Wipe all job-related data from the database (test data reset)."""
    from rich.console import Console
    from src.db import init_db, reset_db
    console = Console()

    if not args.confirm:
        console.print("[yellow]WARNING: This will delete all job data.[/yellow]")
        console.print("Run: python main.py reset --confirm")
        return

    init_db()
    console.print("Clearing database...")
    counts = reset_db()
    for table in ["jobs", "activity_log", "documents", "outcomes"]:
        console.print(f"  {table}: {counts.get(table, 0)} rows deleted")
    console.print("[green]Database cleared. Ready for real use.[/green]")


def cmd_status(args: argparse.Namespace) -> None:
    """Record outcome (reply type) for a job after application."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from src.db import (
        init_db, get_jobs, get_job,
        record_outcome, get_outcomes, get_weekly_summary,
    )

    console = Console()
    init_db()

    # Step 1 — Load and filter eligible jobs
    all_jobs = get_jobs()
    jobs = [j for j in all_jobs if j['status'] in ('applied', 'responded', 'interview')]
    if not jobs:
        console.print("[yellow]No applied jobs to update.[/yellow]")
        return

    # Step 2 — Show selection table
    table = Table(title=f"{len(jobs)} jobs eligible for outcome update")
    table.add_column("#", style="dim", width=4)
    table.add_column("Company", max_width=24)
    table.add_column("Role", max_width=38)
    table.add_column("Status", width=12)
    table.add_column("Score", width=6, justify="center")
    table.add_column("Applied", width=12)
    for i, j in enumerate(jobs, 1):
        score = j.get("score", 0) or 0
        score_cell = f"[green]{score}[/green]" if score >= 7 else (f"[yellow]{score}[/yellow]" if score >= 5 else f"[red]{score}[/red]")
        table.add_row(
            str(i),
            (j.get("company") or "")[:24],
            (j.get("role_title") or "")[:38],
            j.get("status") or "",
            score_cell,
            j.get("applied_at") or "-",
        )
    console.print(table)

    raw = input("Enter job number (or 'q' to quit): ").strip().lower()
    if raw == 'q':
        return
    if not raw.isdigit() or not (1 <= int(raw) <= len(jobs)):
        raw = input("Invalid. Enter job number (or 'q'): ").strip().lower()
        if raw == 'q' or not raw.isdigit() or not (1 <= int(raw) <= len(jobs)):
            return
    job = jobs[int(raw) - 1]
    job_id = job['id']

    # Step 3 — Show existing outcomes
    existing = get_outcomes(job_id)
    if existing:
        console.print(f"\n[dim]Existing outcomes for {job['company']}:[/dim]")
        for o in existing:
            console.print(f"  {o['created_at'][:10]}  {o['reply_type']}  {o['notes'] or ''}")

    # Step 4 — Prompt for outcome type
    console.print("\nOutcome type:")
    console.print("  1) no_reply    -- no response received")
    console.print("  2) rejection   -- rejected by company")
    console.print("  3) positive    -- positive reply or callback")
    console.print("  4) interview   -- interview scheduled or completed")
    console.print("  5) offer       -- job offer received")
    OUTCOME_MAP = {'1': 'no_reply', '2': 'rejection', '3': 'positive', '4': 'interview', '5': 'offer'}
    while True:
        outcome_raw = input("Enter number (1-5): ").strip()
        if outcome_raw in OUTCOME_MAP:
            reply_type = OUTCOME_MAP[outcome_raw]
            break
        console.print("[yellow]Please enter a number between 1 and 5.[/yellow]")

    # Step 5 — Reply date
    date_raw = input("Reply date (YYYY-MM-DD, or Enter to skip): ").strip()
    reply_date = date_raw if date_raw else None

    # Step 6 — Notes
    notes_raw = input("Notes (optional, Enter to skip): ").strip()
    notes = notes_raw if notes_raw else None

    # Step 7 — Confirm and save
    console.print(f"\n  Job:     {job['company']} — {job['role_title']}")
    console.print(f"  Outcome: {reply_type}")
    console.print(f"  Date:    {reply_date or '—'}")
    console.print(f"  Notes:   {notes or '—'}")
    confirm = input("Save? [Y/n]: ").strip().lower()
    if confirm in ('', 'y'):
        record_outcome(job_id, reply_type, reply_date, notes)
        console.print("[green]Outcome recorded.[/green]")
    else:
        console.print("Cancelled.")
        return

    # Step 8 — Weekly summary
    summary = get_weekly_summary()
    if summary is not None:
        panel_text = (
            f"Response rate:                {summary['response_rate']:.0f}%\n"
            f"Avg score (positive replies): {summary['avg_score_responded']:.1f}\n"
            f"Most common outcome:          {summary['top_status']}"
        )
        console.print(Panel(panel_text, title=f"Activity summary ({summary['total_outcomes']} outcomes tracked)"))


def cmd_report(args: argparse.Namespace) -> None:
    """Export an agency activity report for a date range."""
    import sys
    from datetime import datetime
    from rich.console import Console
    from src.report import generate_report

    console = Console()

    raw_from = input("Zeitraum Von (JJJJ-MM-TT): ").strip()
    raw_to = input("Zeitraum Bis (JJJJ-MM-TT): ").strip()

    try:
        datetime.strptime(raw_from, "%Y-%m-%d")
    except ValueError:
        console.print(f"[red]Ungültiges Datum: '{raw_from}'. Format: JJJJ-MM-TT[/red]")
        sys.exit(1)
    try:
        datetime.strptime(raw_to, "%Y-%m-%d")
    except ValueError:
        console.print(f"[red]Ungültiges Datum: '{raw_to}'. Format: JJJJ-MM-TT[/red]")
        sys.exit(1)

    date_from = raw_from.replace("-", "")
    date_to = raw_to.replace("-", "")

    pdf_path, csv_path, count = generate_report(date_from, date_to)
    console.print(f"{count} Einträge gefunden.")
    console.print(str(pdf_path))
    console.print(str(csv_path))


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Job application tracker for Jiri Vosta",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=VERSION,
    )

    subparsers = parser.add_subparsers(title="commands", metavar="<command>")

    fetch_parser = subparsers.add_parser(
        "fetch",
        help="download new Infoagent digests from Forpsi IMAP to inbox/ (Phase 1)",
    )
    fetch_parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        default=None,
        help="download emails from this date (inclusive). Replaces UNSEEN filter.",
    )
    fetch_parser.add_argument(
        "--until",
        metavar="YYYY-MM-DD",
        default=None,
        help="download emails up to and including this date. Requires --since.",
    )
    fetch_parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        default=None,
        help="fetch emails from this exact day only (e.g. 2026-03-31)",
    )
    fetch_parser.set_defaults(func=cmd_fetch)

    subparsers.add_parser(
        "process",
        help="parse inbox emails and score jobs (Phase 1)",
    ).set_defaults(func=cmd_process)

    review_parser = subparsers.add_parser(
        "review",
        help="review scored jobs — approve, reject, or skip (Phase 1)",
    )
    review_parser.add_argument(
        "--all",
        action="store_true",
        help="show all statuses including rejected",
    )
    review_parser.add_argument(
        "--min",
        type=int,
        default=None,
        metavar="N",
        help="show only jobs with score >= N (default: profile min_score_to_show)",
    )
    review_parser.set_defaults(func=cmd_review)

    generate_parser = subparsers.add_parser(
        "generate",
        help="generate tailored CV and cover letter for an approved job (Phase 3)",
    )
    generate_parser.add_argument(
        "--job-id",
        help="job ID to generate documents for (omit to pick from approved list)",
    )
    generate_parser.set_defaults(func=cmd_generate)

    subparsers.add_parser(
        "status",
        help="update job application status — applied, responded, etc. (Phase 4)",
    ).set_defaults(func=cmd_status)

    subparsers.add_parser(
        "report",
        help="export agency activity report for a date range (Phase 2)",
    ).set_defaults(func=cmd_report)

    reset_parser = subparsers.add_parser(
        "reset",
        help="delete all job data from the database (use once to clear P1 test data)",
    )
    reset_parser.add_argument(
        "--confirm",
        action="store_true",
        help="required flag — without it the command does nothing",
    )
    reset_parser.set_defaults(func=cmd_reset)

    return parser


def main() -> None:
    """Parse arguments and dispatch to the correct command handler."""
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
