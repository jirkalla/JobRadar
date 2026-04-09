"""JobRadar — Backfill Wizard.

Interactive wizard to enter past job applications and recruiter contacts
manually. Calls db.py only — no AI, no parser, no scorer.
All activity_log entries use source='manual'.
"""

from datetime import datetime

from rich.console import Console
from rich.panel import Panel

from src import db

console = Console()

STATUS_MAP = {
    "a": "applied",
    "d": "rejected",
    "p": "positive",
    "i": "interview",
    "o": "offer",
}

STATUS_LABELS = {
    "applied": "Applied",
    "rejected": "Declined",
    "positive": "Positive response",
    "interview": "Interview",
    "offer": "Offer",
}


def parse_date(raw: str) -> str:
    """Accept YYYY-MM-DD or DD.MM.YYYY, return YYYY-MM-DD."""
    raw = raw.strip()
    for fmt in ["%Y-%m-%d", "%d.%m.%Y"]:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {raw}. Use YYYY-MM-DD or DD.MM.YYYY")


def date_to_slug(date_iso: str) -> str:
    """Convert YYYY-MM-DD to YYYYMMDD for job ID."""
    return date_iso.replace("-", "")


def enter_job() -> None:
    """Prompt for and save one job application record."""
    company = console.input("[bold]Company:[/bold] ").strip()
    if company.lower() == "done":
        return "done"

    role = console.input("[bold]Role title:[/bold] ").strip()
    if role.lower() == "done":
        return "done"

    while True:
        raw_date = console.input("[bold]Date applied (YYYY-MM-DD or DD.MM.YYYY):[/bold] ").strip()
        if raw_date.lower() == "done":
            return "done"
        try:
            date_iso = parse_date(raw_date)
            break
        except ValueError as e:
            console.print(f"[red]{e}[/red]")

    console.print("\nStatus:")
    console.print("  [A] Applied — no response yet")
    console.print("  [D] Declined by company")
    console.print("  [P] Positive response")
    console.print("  [I] Interview")
    console.print("  [O] Offer")
    while True:
        choice = console.input("Choice: ").strip().lower()
        if choice == "done":
            return "done"
        if choice in STATUS_MAP:
            status = STATUS_MAP[choice]
            break
        console.print("[red]Enter A, D, P, I, or O.[/red]")

    date_slug = date_to_slug(date_iso)

    if db.job_exists_exact(company, role, date_slug):
        console.print(f"[yellow]⚠ Already exists: {company} — {role} — {date_iso}. Skipped.[/yellow]")
        return None

    db.init_db()
    job_id = db.insert_job(
        {"company": company, "role_title": role, "status": status},
        source="manual",
        date_str=date_slug,
    )
    db.log_action(job_id, "applied", source="manual")
    if status == "rejected":
        db.log_action(job_id, "rejected", source="manual")
        db.record_outcome(job_id, "rejection")
    elif status not in ("applied", "new"):
        db.record_outcome(job_id, status)

    label = STATUS_LABELS.get(status, status)
    console.print(f"[green]Saved: {company} — {role} — {date_iso} — {label}[/green]")
    return None


def enter_recruiter() -> None:
    """Prompt for and save one recruiter contact record."""
    agency = console.input("[bold]Agency name:[/bold] ").strip()
    if agency.lower() == "done":
        return "done"

    action = console.input("[bold]Action (e.g. Registration / Job request):[/bold] ").strip()
    if action.lower() == "done":
        return "done"

    while True:
        raw_date = console.input("[bold]Date (YYYY-MM-DD or DD.MM.YYYY):[/bold] ").strip()
        if raw_date.lower() == "done":
            return "done"
        try:
            date_iso = parse_date(raw_date)
            break
        except ValueError as e:
            console.print(f"[red]{e}[/red]")

    outcome = console.input("[bold]Outcome (optional):[/bold] ").strip()
    if outcome.lower() == "done":
        return "done"

    date_slug = date_to_slug(date_iso)

    if db.job_exists_exact(agency, action, date_slug):
        console.print(f"[yellow]⚠ Already exists: {agency} — {action} — {date_iso}. Skipped.[/yellow]")
        return None

    db.init_db()
    job_id = db.insert_job(
        {"company": agency, "role_title": action, "status": "applied"},
        source="manual",
        date_str=date_slug,
    )
    db.log_action(job_id, "recruiter_contact", detail=outcome or None, source="manual")

    console.print(f"[green]Saved: Recruiter contact — {agency} — {date_iso}[/green]")
    return None


def main() -> None:
    db.init_db()
    console.print(Panel("[bold cyan]JobRadar — Backfill Wizard[/bold cyan]\nEnter past job applications. Type 'done' at any prompt to finish."))

    while True:
        console.print("\nRecord type:")
        console.print("  [J] Job application")
        console.print("  [R] Recruiter contact")
        console.print("  [D] Done")
        choice = console.input("Choice: ").strip().lower()

        if choice in ("d", "done"):
            console.print("[bold]Wizard complete.[/bold]")
            break
        elif choice == "j":
            result = enter_job()
            if result == "done":
                console.print("[bold]Wizard complete.[/bold]")
                break
        elif choice == "r":
            result = enter_recruiter()
            if result == "done":
                console.print("[bold]Wizard complete.[/bold]")
                break
        else:
            console.print("[red]Enter J, R, or D.[/red]")


if __name__ == "__main__":
    main()
