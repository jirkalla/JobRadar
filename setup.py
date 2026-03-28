"""First-run setup script for JobRadar.

Creates required folders, initializes the database, and checks config files.
Safe to run multiple times — never overwrites existing files.
"""

import shutil
from pathlib import Path


FOLDERS = [
    Path("config/prompts"),
    Path("src"),
    Path("data/processed"),
    Path("inbox"),
    Path("examples/letters"),
    Path("output/reports"),
    Path("docs"),
    Path("ui/templates"),
]


def create_folders() -> None:
    """Create all required project folders if they do not already exist."""
    for folder in FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"  [ok] {folder}/")


def init_database() -> None:
    """Initialize the SQLite database by calling init_db() from src.db."""
    from src.db import init_db
    db_path = Path("data/tracker.db")
    if db_path.exists():
        print(f"  [ok] data/tracker.db already exists — skipping")
    else:
        init_db()
        print(f"  [ok] data/tracker.db created")


def check_profile() -> None:
    """Ensure config/profile.yaml exists, copying from example if needed."""
    profile = Path("config/profile.yaml")
    example = Path("config/profile.yaml.example")

    if profile.exists():
        print(f"  [ok] config/profile.yaml already exists — skipping")
        return

    if example.exists():
        shutil.copy(example, profile)
        print(f"  [ok] config/profile.yaml copied from example")
        print()
        print("  IMPORTANT: Fill in config/profile.yaml with your details before running.")
    else:
        print("  [warn] config/profile.yaml.example not found — create config/profile.yaml manually")


def main() -> None:
    """Run all setup steps in order."""
    print("JobRadar — setup\n")

    print("Creating folders...")
    create_folders()
    print()

    print("Initializing database...")
    init_database()
    print()

    print("Checking config...")
    check_profile()
    print()

    print("Setup complete. Next step: fill in config/profile.yaml, then run: python main.py --help")


if __name__ == "__main__":
    main()
