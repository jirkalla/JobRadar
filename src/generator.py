"""Document generation layer for JobRadar.

Generates tailored cover letters and CV changes using the AI client.
All terminal interaction lives in main.py — this module is a library.
No print() statements except the heading-not-found warning in apply_cv_changes().
"""

import re
from pathlib import Path

from docx import Document

from src.ai_client import complete, complete_json
from src.db import get_example_letters


def _slugify(value: str, max_len: int = 30) -> str:
    """Lowercase, replace non-alphanumeric chars with hyphens, truncate."""
    value = value.lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = value.strip('-')
    return value[:max_len].rstrip('-')


BANNED_PHRASES = [
    'leverage', 'leveraging', 'excited', 'passionate', 'thrilled',
    'synergy', 'innovative', 'dynamic', 'results-driven', 'detail-oriented',
    'team player', 'hard worker', 'proven track record', 'fast-paced environment',
    'i am writing to express', 'i would like to apply', 'i am confident that',
    'i believe i would be a great fit', 'stabilizing force',
]


def build_cover_letter_prompt(
    profile: dict,
    jd_text: str,
    example_letters: list[dict],
    language: str = 'en',
) -> str:
    """Assemble the cover letter generation prompt.

    Reads config/prompts/generate.txt at runtime — never cached.
    Substitutes all {placeholders} with profile data and examples.

    profile['voice'] is the top-level 'voice:' key from profile.yaml.
    It is a required key — do not use .get() with a fallback.

    example_letters: list of dicts from db.get_example_letters().
    Each dict has keys: id, job_id, doc_type, path, version,
                        rating, use_as_example, created_at.
    """
    prompt_path = Path('config/prompts/generate.txt')
    if not prompt_path.exists():
        raise FileNotFoundError("config/prompts/generate.txt not found.")
    template = prompt_path.read_text(encoding='utf-8')

    # Build examples_section
    if not example_letters:
        examples_section = "No rated examples yet — use the voice document as the only style guide."
    else:
        blocks = []
        for letter in example_letters:
            path = letter['path']
            ext = Path(path).suffix.lower()
            if ext == '.pdf':
                continue
            try:
                if ext == '.docx':
                    doc = Document(path)
                    text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
                else:
                    text = Path(path).read_text(encoding='utf-8')
                blocks.append(
                    f"--- Example letter (rating {letter['rating']}/5) ---\n{text}\n"
                )
            except Exception:
                continue
        if blocks:
            examples_section = '\n\n'.join(blocks)
        else:
            examples_section = "No rated examples yet — use the voice document as the only style guide."

    return template.format(
        name=profile['personal']['name'],
        age=profile['personal']['age'],
        location=profile['personal']['location'],
        voice=profile['voice'],
        skills_expert=', '.join(profile['skills']['expert']),
        skills_solid=', '.join(profile['skills']['solid']),
        job_text=jd_text,
        language='German' if language == 'de' else 'English',
        examples_section=examples_section,
    )


def build_cv_prompt(
    profile: dict,
    jd_text: str,
    base_cv_text: str,
) -> str:
    """Assemble the CV tailoring prompt.

    The AI must respond with JSON only — parsed by the caller via complete_json().
    """
    skills_expert = ', '.join(profile['skills']['expert'])
    skills_solid = ', '.join(profile['skills']['solid'])

    return (
        f"You are tailoring a CV for a job application.\n\n"
        f"CANDIDATE SKILLS:\n"
        f"Expert: {skills_expert}\n"
        f"Solid:  {skills_solid}\n\n"
        f"BASE CV:\n{base_cv_text}\n\n"
        f"JOB DESCRIPTION:\n{jd_text}\n\n"
        f"Task: Propose targeted changes to the professional profile summary only.\n"
        f"Preserve all dates, job titles, company names, and all other content exactly.\n"
        f"skills_to_highlight and skills_to_remove are RECOMMENDATIONS for the human "
        f"to apply manually — they will not be auto-applied to the document.\n\n"
        f"Respond with JSON only. No markdown. No explanation."
    )


def generate_cover_letter(
    client,
    profile: dict,
    jd_text: str,
    language: str = 'en',
) -> str:
    """Generate a cover letter using the AI.

    Fetches up to 3 highest-rated example letters from DB via get_example_letters().
    Returns the cover letter as a plain text string.
    Raises ValueError if the response contains a banned phrase.
    """
    example_letters = get_example_letters(min_rating=4, limit=3)
    prompt = build_cover_letter_prompt(profile, jd_text, example_letters, language)
    text = complete(client, prompt)

    for phrase in BANNED_PHRASES:
        if re.search(r'\b' + re.escape(phrase) + r'\b', text, re.IGNORECASE):
            raise ValueError(
                f"Banned phrase found in output: '{phrase}'. Regenerate or edit manually."
            )

    return text


def generate_cv_changes(
    client,
    profile: dict,
    jd_text: str,
) -> dict:
    """Ask the AI to propose targeted CV changes for this JD.

    Returns a dict with exactly these keys:
      profile_summary, skills_to_highlight, skills_to_remove, changes_explained

    Internally calls extract_base_cv_text(Path('examples/cv_base.docx')) to
    supply base_cv_text to build_cv_prompt(). If cv_base.docx is missing,
    FileNotFoundError propagates to the caller — do NOT catch it here.

    Raises ValueError if:
      - complete_json() cannot parse the response (propagated unchanged)
      - the returned dict is missing any required key

    Does NOT catch any exceptions — let them propagate to the caller (main.py Step 4).
    """
    base_cv_text = extract_base_cv_text(Path('examples/cv_base.docx'))
    prompt = build_cv_prompt(profile, jd_text, base_cv_text)
    result = complete_json(client, prompt)

    REQUIRED_CV_KEYS = {'profile_summary', 'skills_to_highlight', 'skills_to_remove', 'changes_explained'}
    missing = REQUIRED_CV_KEYS - result.keys()
    if missing:
        raise ValueError(f"AI response missing required keys: {missing}")

    return result


def extract_base_cv_text(cv_path: Path) -> str:
    """Extract plain text from examples/cv_base.docx for use in the CV prompt.

    Returns all non-empty paragraph texts joined with newlines.
    Raises FileNotFoundError if the file does not exist.
    Never modifies the source file.
    """
    if not cv_path.exists():
        raise FileNotFoundError(f"CV file not found: {cv_path}")
    doc = Document(cv_path)
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    return '\n'.join(lines)


def apply_cv_changes(
    cv_path: Path,
    changes: dict,
    output_path: Path,
) -> None:
    """Apply the AI-proposed profile summary to the base CV and save as a new .docx.

    Only the profile summary paragraph is replaced. Skills changes are NOT
    applied — they are recommendations for the user to apply manually.

    Reads from cv_path. Writes to output_path. Never touches cv_base.docx.
    """
    doc = Document(cv_path)
    replace_next = False
    replaced = False

    for p in doc.paragraphs:
        style_name = p.style.name
        is_heading = (
            style_name.lower().startswith('heading')
            or 'berschrift' in style_name
        )

        if replace_next and p.text.strip():
            for run in p.runs:
                run.text = ''
            if p.runs:
                p.runs[0].text = changes['profile_summary']
            else:
                p.add_run(changes['profile_summary'])
            replace_next = False
            replaced = True
            break

        if is_heading:
            lower_text = p.text.lower()
            if any(kw in lower_text for kw in ('profile', 'summary', 'about', 'profil')):
                replace_next = True

    if not replaced:
        doc.add_paragraph(changes['profile_summary'])
        print("Warning: profile summary heading not found — summary appended. Review before sending.")

    doc.save(output_path)


def write_cover_letter_docx(
    text: str,
    output_path: Path,
    profile: dict,
) -> None:
    """Write cover letter text to a .docx file.

    Structure: name heading, blank line, body paragraphs split on double newline.
    """
    doc = Document()
    doc.add_heading(profile['personal']['name'], level=1)
    doc.add_paragraph('')
    for chunk in text.split('\n\n'):
        if chunk.strip():
            doc.add_paragraph(chunk.strip())
    doc.save(output_path)


def make_output_dir(company: str, role_title: str, date_str: str) -> Path:
    """Build and return the output directory Path. Does NOT create it.

    Caller is responsible for mkdir().

    Naming: output/{date_str}_{company-slug}_{role-slug}/
    date_str format: YYYY-MM-DD
    """
    return Path('output') / f"{date_str}_{_slugify(company)}_{_slugify(role_title)}"
