"""
Weekly stale-job nudge — emails employers whose active role has had
no applications in the last N days (default 14), with one specific
AI-drafted suggestion for improving it.

Run via cron (Render scheduled job):

    python manage.py nudge_stale_jobs
    python manage.py nudge_stale_jobs --dry-run
    python manage.py nudge_stale_jobs --stale-days 21
"""
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Count, Max, Q
from django.urls import reverse
from django.utils import timezone

from jobs.models import Job


NUDGE_SYSTEM_PROMPT = """You write a short, candid email to an employer whose flexible job listing has gone quiet on Hirely (no applications recently).

Rules:
- Output ONLY the email body. No subject, no greeting, no sign-off (we add "— Hirely").
- 2–3 short sentences. Warm but candid — they want to know what's actually wrong.
- Suggest ONE specific, concrete improvement based on what's likely missing from the listing
  (clearer hours, salary range, remote vs on-site clarity, tighter description, more specific
  requirements). Pick the strongest single nudge — never give a list.
- Never invent feedback from candidates. Never claim you know why parents passed.
- End with one small actionable next step ("a 2-minute edit usually helps").
"""


def _draft_nudge(job):
    """Use Claude to write a tailored nudge. None if AI unavailable."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    try:
        from anthropic import Anthropic, APIError
    except ImportError:
        return None

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = (
        f"Role: {job.title} at {job.company}\n"
        f"Schedule: {job.get_schedule_type_display()}"
        f"{' · Remote' if job.is_remote else ''}"
        f"{f' · {job.hours_per_day} hrs/day' if job.hours_per_day else ''}\n"
        f"Pay: {job.salary or '(not specified)'}\n"
        f"Location: {job.location or '(not specified)'}\n"
        f"Description: {(job.description or '')[:400]}\n"
        f"Requirements: {(job.requirements or '(none)')[:200]}\n\n"
        f"Posted {(timezone.now() - job.created_at).days} days ago. No applications.\n"
        f"Write the nudge now."
    )
    try:
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=220,
            system=NUDGE_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}],
        )
    except APIError:
        return None
    return ''.join(
        b.text for b in resp.content if getattr(b, 'type', None) == 'text'
    ).strip() or None


class Command(BaseCommand):
    help = 'Email employers whose active role has had no applications recently.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Print emails to stdout instead of sending.')
        parser.add_argument('--stale-days', type=int, default=14,
                            help='How many days of zero applications counts as stale.')
        parser.add_argument('--base-url', type=str,
                            default='https://hirely.onrender.com',
                            help='Base URL used to build the edit-job link.')

    def handle(self, *args, **opts):
        now = timezone.now()
        cutoff = now - timedelta(days=opts['stale_days'])
        base_url = opts['base_url'].rstrip('/')

        # Active jobs posted before cutoff AND with no recent applications.
        candidates = (
            Job.objects
            .filter(is_active=True, created_at__lt=cutoff)
            .annotate(
                app_count=Count('applications'),
                last_app=Max('applications__applied_at'),
            )
            .filter(Q(last_app__isnull=True) | Q(last_app__lt=cutoff))
            .select_related('posted_by')
        )

        sent = skipped = 0
        for job in candidates:
            employer = job.posted_by
            if not employer.email:
                skipped += 1
                continue

            body = _draft_nudge(job)
            if not body:
                # Fallback nudge that's still useful — never silent.
                missing = []
                if not job.salary:
                    missing.append("a pay rate (parents budget carefully)")
                if not job.hours_per_day and job.schedule_type != 'anytime':
                    missing.append("a typical hours-per-day number")
                if not job.location and not job.is_remote:
                    missing.append("a location or a clear remote flag")
                if missing:
                    body = (
                        f"Your role \"{job.title}\" has been quiet on Hirely. "
                        f"The most common reason parents skip a listing is missing context — "
                        f"in your case, adding {missing[0]} usually helps a lot. A 2-minute edit could be worth it."
                    )
                else:
                    body = (
                        f"Your role \"{job.title}\" has been quiet on Hirely lately. "
                        f"Sometimes tightening the description or being more specific about the "
                        f"week-to-week reality of the work is enough to bring it back."
                    )

            edit_url = f"{base_url}{reverse('edit_job', args=[job.pk])}"
            subject = f"Your role \"{job.title}\" has gone quiet"
            message = f"Hi,\n\n{body}\n\nEdit it here:\n{edit_url}\n\n— Hirely"

            if opts['dry_run']:
                self.stdout.write(self.style.NOTICE(f'\n--- TO: {employer.email} ---'))
                self.stdout.write(f'Subject: {subject}\n')
                self.stdout.write(message)
                self.stdout.write(self.style.NOTICE('--- END ---\n'))
                sent += 1
                continue

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[employer.email],
                fail_silently=True,
            )
            sent += 1

        self.stdout.write(self.style.SUCCESS(
            f'Stale-job nudges: {sent} sent, {skipped} skipped.'
        ))
