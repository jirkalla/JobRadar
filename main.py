"""JobRadar CLI — job application tracker for Jiri Vosta.

Entry point for all CLI commands. This file orchestrates — it never
contains business logic. All real work is done in src/ modules.
"""

import argparse
import shutil
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


VERSION = "job-tracker v0.1.0"


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
    from src.db import insert_job, job_exists_for_eml
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


def cmd_review(args: argparse.Namespace) -> None:
    """Review and approve or reject scored jobs."""
    print("Coming in Phase 1: review scored jobs")


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate a tailored CV and cover letter for an approved job."""
    print("Coming in Phase 3: generate CV and cover letter")


def cmd_status(args: argparse.Namespace) -> None:
    """Update the status of a job application."""
    print("Coming in Phase 4: update job status")


def cmd_report(args: argparse.Namespace) -> None:
    """Export an agency activity report for a date range."""
    print("Coming in Phase 2: export agency report")


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

    subparsers.add_parser(
        "process",
        help="parse inbox emails and score jobs (Phase 1)",
    ).set_defaults(func=cmd_process)

    subparsers.add_parser(
        "review",
        help="review scored jobs — approve, reject, or skip (Phase 1)",
    ).set_defaults(func=cmd_review)

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
