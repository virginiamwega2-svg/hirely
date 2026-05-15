"""
CV / resume parsing for Hirely.

Given an uploaded file (PDF / DOCX), extract plain text and ask
Claude to return strict JSON with the structured fields we use to
power job matching, personalised chat answers, and the digest.

All public functions are safe to call without checking the API key —
they fall back to "do nothing" when ANTHROPIC_API_KEY is empty so
the rest of the apply flow keeps working.
"""
from __future__ import annotations

import io
import json
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def extract_text(uploaded_file) -> str:
    """Extract plain text from a Django UploadedFile. Returns '' on failure."""
    name = (uploaded_file.name or '').lower()
    try:
        uploaded_file.seek(0)
        data = uploaded_file.read()
        uploaded_file.seek(0)
    except Exception:
        logger.exception('resume_parser: could not read upload')
        return ''

    if name.endswith('.pdf'):
        try:
            from pdfminer.high_level import extract_text as pdf_extract
            return pdf_extract(io.BytesIO(data)) or ''
        except Exception:
            logger.exception('resume_parser: pdf extraction failed')
            return ''

    if name.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(io.BytesIO(data))
            return '\n'.join(p.text for p in doc.paragraphs)
        except Exception:
            logger.exception('resume_parser: docx extraction failed')
            return ''

    if name.endswith('.txt'):
        try:
            return data.decode('utf-8', errors='ignore')
        except Exception:
            return ''

    return ''


PARSE_SYSTEM_PROMPT = """You extract a structured profile from a parent's CV/resume.

Output STRICT JSON ONLY — no prose, no fences. Shape:
{
  "years_experience": <integer 0-50, your best estimate from work history, or 0 if unclear>,
  "top_skills": "<up to 6 comma-separated skills, plain English, lowercase phrases ok>",
  "location_hint": "<city or region if mentioned, else \\"\\">",
  "schedule_preference": "<short phrase if the CV hints at availability ('mornings only', 'term-time', 'evenings'), else \\"\\">",
  "summary": "<one or two warm sentences a parent would actually recognise as themselves; max 280 chars; never invent specifics not in the CV>"
}

Rules:
- Use ONLY what's in the CV. If a field has no signal, return an empty string (or 0 for years_experience).
- The summary should be parent-friendly, not corporate. Examples:
  good: "Eight years admin experience, mostly remote, last two years as a virtual assistant."
  bad:  "Highly motivated team player with synergistic communication skills."
- Skills should be concrete capabilities, not buzzwords. Prefer "spreadsheet automation" over "detail-oriented".
"""


def parse_with_claude(text: str) -> Optional[dict]:
    """Send extracted CV text to Claude → structured dict. None on error."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    if not text or not text.strip():
        return None

    try:
        from anthropic import Anthropic, APIError
    except ImportError:
        return None

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    # Cap input length — CVs are short, but be defensive against huge dumps.
    snippet = text[:8000]

    try:
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=500,
            system=PARSE_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': f'CV text:\n\n{snippet}'}],
        )
    except APIError:
        logger.exception('resume_parser: anthropic call failed')
        return None

    raw = ''.join(b.text for b in resp.content if getattr(b, 'type', None) == 'text').strip()
    if raw.startswith('```'):
        raw = raw.strip('`').lstrip('json').strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning('resume_parser: bad JSON from model: %r', raw[:200])
        return None

    # Clamp / sanitise.
    years = data.get('years_experience') or 0
    try:
        years = max(0, min(int(years), 50))
    except (TypeError, ValueError):
        years = 0

    return {
        'years_experience':    years,
        'top_skills':          str(data.get('top_skills', ''))[:400],
        'location_hint':       str(data.get('location_hint', ''))[:120],
        'schedule_preference': str(data.get('schedule_preference', ''))[:120],
        'summary':             str(data.get('summary', ''))[:400],
    }


def parse_and_save(user, uploaded_file) -> bool:
    """High-level helper: extract text → call Claude → persist to ParentProfile.
    Returns True on success, False otherwise. Never raises."""
    from .models import ParentProfile

    try:
        text = extract_text(uploaded_file)
        if not text.strip():
            ParentProfile.objects.update_or_create(
                user=user,
                defaults={'parse_failed': True},
            )
            return False

        parsed = parse_with_claude(text)
        if parsed is None:
            ParentProfile.objects.update_or_create(
                user=user,
                defaults={'raw_resume_text': text[:20000], 'parse_failed': True},
            )
            return False

        ParentProfile.objects.update_or_create(
            user=user,
            defaults={
                'raw_resume_text': text[:20000],
                'parse_failed': False,
                **parsed,
            },
        )
        return True
    except Exception:
        logger.exception('resume_parser.parse_and_save crashed')
        return False
