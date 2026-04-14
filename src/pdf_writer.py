"""PDF generation from Markdown source files.

Converts .md CV and cover letter files to print-ready A4 PDFs.
No AI calls. No DB calls. reportlab only.
"""

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

DARK   = colors.HexColor("#1a1a2e")
ACCENT = colors.HexColor("#2d6a9f")
GREY   = colors.HexColor("#666666")


def _render_inline(raw: str) -> str:
    """Escape XML special chars and convert **bold** to reportlab <b> tags."""
    raw = raw.replace('&', '&amp;')
    raw = raw.replace('<', '&lt;').replace('>', '&gt;')
    raw = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', raw)
    return raw


def _hr() -> HRFlowable:
    return HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#dddddd"),
        spaceAfter=1 * mm, spaceBefore=0,
    )


def cv_md_to_pdf(md_path: Path, output_path: Path) -> None:
    """Convert a CV markdown file to a styled A4 PDF.

    Parses the MD structure produced by cv_base.md and apply_cv_changes():
      # Name
      **Role Title**
      contact | line | here
      ---
      ## Section Heading
      ### Job Title
      **Employer | Location | Dates**
      - bullet point
      | skill label | skill value |

    Raises FileNotFoundError if md_path does not exist.
    """
    if not md_path.exists():
        raise FileNotFoundError(f"CV source not found: {md_path}")

    lines = md_path.read_text(encoding='utf-8').splitlines()

    name_style = ParagraphStyle("name", fontSize=22, textColor=DARK,
        fontName="Helvetica-Bold", spaceAfter=1 * mm, leading=26)
    title_style = ParagraphStyle("title", fontSize=11, textColor=ACCENT,
        fontName="Helvetica", spaceAfter=3 * mm, leading=14)
    contact_style = ParagraphStyle("contact", fontSize=9, textColor=GREY,
        fontName="Helvetica", spaceAfter=0, leading=13)
    section_style = ParagraphStyle("section", fontSize=10, textColor=ACCENT,
        fontName="Helvetica-Bold", spaceBefore=5 * mm, spaceAfter=1.5 * mm,
        leading=13)
    job_title_style = ParagraphStyle("jobtitle", fontSize=10, textColor=DARK,
        fontName="Helvetica-Bold", spaceAfter=0.5 * mm, leading=13)
    employer_style = ParagraphStyle("employer", fontSize=9.5, textColor=GREY,
        fontName="Helvetica", spaceAfter=2 * mm, leading=13)
    body_style = ParagraphStyle("body", fontSize=9.5, textColor=DARK,
        fontName="Helvetica", spaceAfter=2 * mm, leading=14)
    bullet_style = ParagraphStyle("bullet", fontSize=9.5, textColor=DARK,
        fontName="Helvetica", spaceAfter=1.5 * mm, leading=14,
        leftIndent=8 * mm, firstLineIndent=-4 * mm)
    skills_label = ParagraphStyle("skillslabel", fontSize=9, textColor=GREY,
        fontName="Helvetica-Bold", leading=13)
    skills_value = ParagraphStyle("skillsval", fontSize=9.5, textColor=DARK,
        fontName="Helvetica", leading=13)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
    )

    story = []
    prev_was_h1 = False
    header_done = False  # True after first ## heading; disables contact-line detection
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # H1 — name (single # only)
        if re.match(r'^# [^#]', stripped):
            story.append(Paragraph(stripped[2:], name_style))
            prev_was_h1 = True
            i += 1
            continue

        # Bold-only line immediately after H1 — role title
        if (prev_was_h1 and stripped.startswith('**')
                and stripped.endswith('**') and stripped.count('**') == 2):
            story.append(Paragraph(stripped[2:-2], title_style))
            prev_was_h1 = False
            i += 1
            continue

        prev_was_h1 = False

        # Contact line — contains | but is NOT a table row.
        # Only fires before the first ## section heading (header_done = False).
        # Employer/education lines also contain | but appear after a ## heading.
        if (not header_done and '|' in stripped
                and not stripped.startswith('#')
                and not stripped.startswith('|')):
            contact = stripped.replace('|', '&#160;&#160;|&#160;&#160;')
            story.append(Paragraph(contact, contact_style))
            story.append(Spacer(1, 3 * mm))
            story.append(_hr())
            i += 1
            continue

        # H2 — section heading
        if re.match(r'^## [^#]', stripped):
            header_done = True
            story.append(Paragraph(stripped[3:], section_style))
            i += 1
            continue

        # H3 — job title, followed by employer line
        if re.match(r'^### [^#]', stripped):
            story.append(Paragraph(stripped[4:], job_title_style))
            i += 1
            if i < len(lines):
                next_stripped = lines[i].strip()
                if next_stripped.startswith('**') and next_stripped.endswith('**'):
                    employer = re.sub(r'\*\*(.+?)\*\*', r'\1', next_stripped)
                    employer = employer.replace('|', '&#160;&#160;|&#160;&#160;')
                    story.append(Paragraph(employer, employer_style))
                    i += 1
            continue

        # Skills table row | label | value |
        # Rows without exactly 2 non-empty cells (e.g. | | | header) are skipped.
        if (stripped.startswith('|') and stripped.endswith('|')
                and '---' not in stripped):
            cells = [c.strip() for c in stripped.split('|') if c.strip()]
            if len(cells) == 2:
                label = re.sub(r'\*\*(.+?)\*\*', r'\1', cells[0])
                t = Table(
                    [[Paragraph(label, skills_label),
                      Paragraph(cells[1], skills_value)]],
                    colWidths=[42 * mm, 130 * mm],
                )
                t.setStyle(TableStyle([
                    ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING",    (0, 0), (-1, -1), 1),
                ]))
                story.append(t)
            i += 1
            continue

        # Table separator row
        if '---' in stripped and stripped.startswith('|'):
            i += 1
            continue

        # Bullet point
        if stripped.startswith('- '):
            content = _render_inline(stripped[2:])
            story.append(
                Paragraph(f"&#8226;&#160;&#160;{content}", bullet_style)
            )
            i += 1
            continue

        # Horizontal rule — skip; section headings provide visual separation
        # and the contact line handler already adds an HR after the header block.
        if stripped == '---':
            i += 1
            continue

        # Empty line
        if not stripped:
            story.append(Spacer(1, 1 * mm))
            i += 1
            continue

        # Default — body paragraph
        story.append(Paragraph(_render_inline(stripped), body_style))
        i += 1

    doc.build(story)


def cover_letter_md_to_pdf(md_path: Path, output_path: Path) -> None:
    """Convert a cover letter markdown file to a clean A4 PDF.

    Expects the exact structure written by write_cover_letter_md() in generator.py:
      <!-- SENDER_START -->
      **Name**
      email · phone
      location
      <!-- SENDER_END -->
      (blank)
      date
      (blank)
      company
      (blank)
      salutation
      (blank)
      body paragraphs separated by blank lines
      (blank)
      sign-off
      (blank)
      name

    Coupled to write_cover_letter_md() in src/generator.py — any structural
    change there must be reflected here in the same commit.

    Raises FileNotFoundError if md_path does not exist.
    """
    if not md_path.exists():
        raise FileNotFoundError(f"Cover letter source not found: {md_path}")

    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()

    sender_name_style = ParagraphStyle("cl_name", fontSize=11, textColor=DARK,
        fontName="Helvetica-Bold", leading=14, spaceAfter=1 * mm)
    sender_meta_style = ParagraphStyle("cl_meta", fontSize=9.5, textColor=GREY,
        fontName="Helvetica", leading=13, spaceAfter=0)
    date_style = ParagraphStyle("cl_date", fontSize=10, textColor=DARK,
        fontName="Helvetica", leading=13, spaceAfter=0)
    company_style = ParagraphStyle("cl_company", fontSize=10, textColor=DARK,
        fontName="Helvetica-Bold", leading=13, spaceAfter=0)
    salutation_style = ParagraphStyle("cl_salutation", fontSize=10,
        textColor=DARK, fontName="Helvetica", leading=13, spaceAfter=2 * mm)
    body_style = ParagraphStyle("cl_body", fontSize=10, textColor=DARK,
        fontName="Helvetica", leading=15, spaceAfter=4 * mm)
    signoff_style = ParagraphStyle("cl_signoff", fontSize=10, textColor=DARK,
        fontName="Helvetica", leading=14, spaceAfter=0)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )

    # Parse sender block using explicit delimiters
    in_sender = False
    sender_lines: list[str] = []
    body_lines: list[str] = []

    for line in lines:
        if line.strip() == '<!-- SENDER_START -->':
            in_sender = True
            continue
        if line.strip() == '<!-- SENDER_END -->':
            in_sender = False
            continue
        if in_sender:
            sender_lines.append(line.strip())
        else:
            body_lines.append(line)

    story = []

    # Render sender block
    if sender_lines:
        name_line = re.sub(r'\*\*(.+?)\*\*', r'\1', sender_lines[0])
        story.append(Paragraph(name_line, sender_name_style))
        for meta in sender_lines[1:]:
            if meta:
                story.append(Paragraph(_render_inline(meta), sender_meta_style))
        story.append(Spacer(1, 8 * mm))

    # Parse body section by position:
    # non_empty[0] = date, [1] = company, [2] = salutation,
    # [3:-2] = body paragraphs, [-2] = sign-off, [-1] = name
    non_empty = [ln for ln in body_lines if ln.strip()]

    if len(non_empty) < 3:
        # Fallback: render everything as body
        for line in body_lines:
            if line.strip():
                story.append(Paragraph(_render_inline(line.strip()), body_style))
    else:
        date_line    = non_empty[0]
        company_line = non_empty[1]
        salutation   = non_empty[2]
        sign_off     = non_empty[-2]
        sign_name    = non_empty[-1]
        body_content = non_empty[3:-2]

        story.append(Paragraph(_render_inline(date_line), date_style))
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(_render_inline(company_line), company_style))
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(_render_inline(salutation), salutation_style))

        for para in body_content:
            story.append(Paragraph(_render_inline(para), body_style))

        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(_render_inline(sign_off), signoff_style))
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph(_render_inline(sign_name), signoff_style))

    doc.build(story)
