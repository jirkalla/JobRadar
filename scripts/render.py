"""Render script — rebuild full markdown and regenerate PDF after editing.

Usage:
    # After editing a cover letter body:
    python scripts/render.py output/20260412/smartly/cl_20260412_smartly_body.md

    # After editing a CV:
    python scripts/render.py output/20260412/smartly/cv_20260412_smartly.md

Detects document type from filename:
    *_body.md  -> Cover Letter (rebuilds full .md from letterhead + new body)
    cv_*.md    -> CV (regenerates PDF from edited .md directly)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_conn, rate_document
from src.pdf_writer import cover_letter_md_to_pdf, cv_md_to_pdf


def _rebuild_cover_letter(body_path: Path, full_md_path: Path) -> None:
    """Reconstruct full cover letter .md from existing letterhead + updated body."""
    if not full_md_path.exists():
        raise FileNotFoundError(f"Full cover letter not found: {full_md_path}")

    existing = full_md_path.read_text(encoding="utf-8")
    new_body = body_path.read_text(encoding="utf-8").strip()

    # Normalise body paragraphs
    body_paragraphs = [p.strip() for p in new_body.split("\n\n") if p.strip()]
    new_body_text = "\n\n".join(body_paragraphs)

    lines = existing.splitlines()

    # Find salutation line (line after <!-- SENDER_END --> block, company, date etc.)
    # Structure: sender block, blank, date, blank, company, blank, salutation, blank, BODY, blank, signoff, blank, name
    # Locate salutation by finding the last line that starts with "Dear " or "Sehr geehrte"
    salutation_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("Dear ") or stripped.startswith("Sehr geehrte"):
            salutation_idx = i
            break

    if salutation_idx is None:
        raise ValueError(f"Could not locate salutation line in {full_md_path}")

    # Find signoff — scan backwards from end: "Best regards," / "Mit freundlichen Grüßen,"
    signoff_idx = None
    for i in range(len(lines) - 1, salutation_idx, -1):
        stripped = lines[i].strip()
        if stripped in ("Best regards,", "Mit freundlichen Grüßen,"):
            signoff_idx = i
            break

    if signoff_idx is None:
        raise ValueError(f"Could not locate signoff line in {full_md_path}")

    # Reconstruct: everything up to and including salutation + blank line,
    # then new body, then blank line + signoff onwards
    header_lines = lines[: salutation_idx + 1]  # includes salutation
    footer_lines = lines[signoff_idx - 1 :]      # blank line before signoff + signoff + name

    reconstructed = "\n".join(header_lines) + "\n\n" + new_body_text + "\n\n" + "\n".join(footer_lines)

    full_md_path.write_text(reconstructed, encoding="utf-8")


def _find_doc_id(path: Path) -> tuple[int | None, int | None]:
    """Return (doc_id, current_rating) by matching path in documents table, or (None, None)."""
    path_str = str(path)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, rating FROM documents WHERE path = ?", (path_str,)
        ).fetchone()
    if row:
        return row[0], row[1]
    return None, None


def _prompt_rating(doc_id: int, current_rating: int | None) -> None:
    """Prompt user for an optional rating update."""
    current_str = f" (current: {current_rating})" if current_rating else ""
    raw = input(f"Update rating 1-5{current_str}? (Enter to skip): ").strip()
    if not raw:
        print("  Rating skipped.")
        return
    if raw.isdigit() and 1 <= int(raw) <= 5:
        rating = int(raw)
        rate_document(doc_id, rating)
        example = rating >= 4
        print(f"  ✓ Rating: {rating} saved (use_as_example={example})")
    else:
        print(f"  Invalid input '{raw}' — rating skipped.")


def render_cover_letter(body_path: Path) -> None:
    """Rebuild full .md and regenerate PDF for a cover letter."""
    folder = body_path.parent
    stem = body_path.stem  # e.g. cl_20260412_smartly_body

    if not stem.endswith("_body"):
        raise ValueError(f"Expected filename ending in _body.md, got: {body_path.name}")

    base_stem = stem[: -len("_body")]  # e.g. cl_20260412_smartly
    full_md_path = folder / f"{base_stem}.md"
    pdf_path = folder / f"{base_stem}.pdf"

    print(f"Cover letter: {body_path.name}")
    print(f"  Rebuilding {full_md_path.name}...")
    _rebuild_cover_letter(body_path, full_md_path)
    print(f"  ✓ {full_md_path.name} updated")

    print(f"  Regenerating {pdf_path.name}...")
    cover_letter_md_to_pdf(full_md_path, pdf_path)
    print(f"  ✓ {pdf_path.name} regenerated")

    doc_id, current_rating = _find_doc_id(body_path)
    if doc_id is None:
        print("  ⚠ Document not found in DB — rating skipped.")
    else:
        _prompt_rating(doc_id, current_rating)


def render_cv(md_path: Path) -> None:
    """Regenerate PDF for a CV from its (edited) markdown file."""
    pdf_path = md_path.with_suffix(".pdf")

    print(f"CV: {md_path.name}")
    print(f"  Regenerating {pdf_path.name}...")
    cv_md_to_pdf(md_path, pdf_path)
    print(f"  ✓ {pdf_path.name} regenerated")

    doc_id, current_rating = _find_doc_id(md_path)
    if doc_id is None:
        print("  ⚠ Document not found in DB — rating skipped.")
    else:
        _prompt_rating(doc_id, current_rating)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/render.py <path-to-body.md-or-cv.md>")
        sys.exit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    name = input_path.name
    if name.endswith("_body.md"):
        render_cover_letter(input_path)
    elif name.startswith("cv_") and name.endswith(".md"):
        render_cv(input_path)
    else:
        print(
            f"Error: cannot detect document type from filename '{name}'.\n"
            "Expected: *_body.md for cover letters, cv_*.md for CVs."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
