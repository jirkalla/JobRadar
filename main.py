"""JobRadar CLI — job application tracker for Jiri Vosta.

Entry point for all CLI commands. This file orchestrates — it never
contains business logic. All real work is done in src/ modules.
"""

import argparse
from pathlib import Path


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


def cmd_process(args: argparse.Namespace) -> None:
    """Parse inbox emails and score jobs."""
    print("Coming in Phase 1: parse inbox and score jobs")


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
