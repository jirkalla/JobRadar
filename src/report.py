"""Agency activity report — PDF + CSV export in German.

Reads job activity from the database and exports:
- A4 PDF with page header (name, address, date range) and German-labelled table
- CSV with the same columns and German labels

Call generate_report(date_from, date_to) to produce both files.
Date arguments must be YYYYMMDD strings (e.g. '20251001').
"""

import csv
from datetime import datetime
from pathlib import Path

import yaml
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from src.db import get_activity_report


ACTION_LABELS: dict[str, str] = {
    "applied": "Beworben",
    "recruiter_contact": "Kontakt Recruiter",
    "approved": "Genehmigt",
    "rejected": "Abgelehnt",
    "responded": "Antwort erhalten",
    "interview": "Vorstellungsgespräch",
    "offer": "Angebot",
    "scored": "Bewertet",
}

STATUS_LABELS: dict[str, str] = {
    "new": "Neu",
    "approved": "Genehmigt",
    "applied": "Beworben",
    "responded": "Antwort",
    "rejected": "Abgelehnt",
    "closed": "Abgeschlossen",
}

OUTPUT_DIR = Path("output/reports")


def _load_profile() -> dict:
    """Return config/profile.yaml as a dict."""
    return yaml.safe_load(Path("config/profile.yaml").read_text(encoding="utf-8"))


def _fmt_date_display(yyyymmdd: str) -> str:
    """Convert YYYYMMDD to DD.MM.YYYY for display."""
    return datetime.strptime(yyyymmdd, "%Y%m%d").strftime("%d.%m.%Y")


def _row_aktion(row: dict) -> str:
    """Return German Aktion label, appending ' (M)' for manual entries.

    Manual detection: row.get('source') == 'manual'.
    If source is NULL (no activity_log row), treats as non-manual.
    """
    return ACTION_LABELS.get(row.get("action") or "", row.get("action") or "-")


def _build_table_data(rows: list[dict]) -> list[list[str]]:
    """Convert DB rows to a list of string rows (header + data) for the table."""
    header = ["Datum", "Unternehmen", "Position", "Status"]
    data: list[list[str]] = [header]
    for row in rows:
        datum = _fmt_date_display(row["applied_at"]) if row.get("applied_at") else "-"
        position = (row.get("role_title") or "")[:45]
        status = STATUS_LABELS.get(row.get("status") or "", row.get("status") or "-")
        data.append([datum, row.get("company") or "-", position, status])
    return data


def _draw_page_header(
    canvas: object,
    doc: object,
    profile: dict,
    date_from: str,
    date_to: str,
) -> None:
    """Draw the report header block and page-number footer on each page."""
    canvas.saveState()  # type: ignore[attr-defined]
    page_width, page_height = A4

    # Title
    canvas.setFont("Helvetica-Bold", 14)  # type: ignore[attr-defined]
    canvas.drawString(20 * mm, page_height - 18 * mm, "Nachweis der Bewerbungsaktivitäten")  # type: ignore[attr-defined]

    # Header block
    name: str = profile["personal"]["name"]
    date_from_disp = _fmt_date_display(date_from)
    date_to_disp = _fmt_date_display(date_to)
    zeitraum = f"{date_from_disp} - {date_to_disp}"
    erstellt = datetime.now().strftime("%d.%m.%Y")

    label_x = 20 * mm
    value_x = 50 * mm
    y = page_height - 27 * mm
    line_h = 5.5 * mm

    for label, value in [
        ("Name:", name),
        ("Zeitraum:", zeitraum),
        ("Erstellt am:", erstellt),
    ]:
        canvas.setFont("Helvetica-Bold", 9)  # type: ignore[attr-defined]
        canvas.drawString(label_x, y, label)  # type: ignore[attr-defined]
        canvas.setFont("Helvetica", 9)  # type: ignore[attr-defined]
        canvas.drawString(value_x, y, value)  # type: ignore[attr-defined]
        y -= line_h

    # Separator line below header
    canvas.setStrokeColor(colors.HexColor("#999999"))  # type: ignore[attr-defined]
    canvas.line(20 * mm, y - 1 * mm, page_width - 20 * mm, y - 1 * mm)  # type: ignore[attr-defined]

    # Page footer
    canvas.setFont("Helvetica", 8)  # type: ignore[attr-defined]
    canvas.setFillColor(colors.grey)  # type: ignore[attr-defined]
    canvas.drawString(20 * mm, 8 * mm, f"Seite {doc.page}")  # type: ignore[attr-defined]

    canvas.restoreState()  # type: ignore[attr-defined]


def _generate_pdf(
    table_data: list[list[str]],
    pdf_path: Path,
    profile: dict,
    date_from: str,
    date_to: str,
) -> None:
    """Write the A4 PDF report to pdf_path."""
    header_height = 55 * mm
    margin = 20 * mm

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=header_height,
        bottomMargin=18 * mm,
    )

    # Column widths — total ~175mm to fill A4 body
    col_widths = [22 * mm, 50 * mm, 80 * mm, 23 * mm]

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "body_cell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.black,
    )
    header_style = ParagraphStyle(
        "header_cell",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    formatted: list[list[Paragraph]] = []
    for i, row in enumerate(table_data):
        style = header_style if i == 0 else body_style
        formatted.append([Paragraph(cell, style) for cell in row])

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#404040")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    # Alternating row backgrounds for data rows
    for i in range(1, len(table_data)):
        bg = colors.white if i % 2 == 1 else colors.HexColor("#f0f0f0")
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

    table = Table(formatted, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(style_cmds))

    doc.build(
        [table],
        onFirstPage=lambda c, d: _draw_page_header(c, d, profile, date_from, date_to),
        onLaterPages=lambda c, d: _draw_page_header(c, d, profile, date_from, date_to),
    )


def _generate_csv(table_data: list[list[str]], csv_path: Path) -> None:
    """Write the CSV report to csv_path (UTF-8 with BOM for Excel compatibility)."""
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(table_data)


def generate_report(date_from: str, date_to: str) -> tuple[Path, Path, int]:
    """Generate PDF and CSV reports for the given date range.

    Args:
        date_from: Start date in YYYYMMDD format (inclusive).
        date_to: End date in YYYYMMDD format (inclusive).

    Returns:
        Tuple of (pdf_path, csv_path, entry_count).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    profile = _load_profile()
    rows = get_activity_report(date_from, date_to)
    table_data = _build_table_data(rows)
    entry_count = len(rows)

    pdf_path = OUTPUT_DIR / f"bericht_{date_from}_bis_{date_to}.pdf"
    csv_path = OUTPUT_DIR / f"bericht_{date_from}_bis_{date_to}.csv"

    _generate_pdf(table_data, pdf_path, profile, date_from, date_to)
    _generate_csv(table_data, csv_path)

    return pdf_path, csv_path, entry_count
