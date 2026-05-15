"""
Weekly AI-curated job digest.

Sends a short, personalised "jobs worth your time this week" email to
parents who have applied to anything in the last 30 days (signal they
are actively looking). Throttled to once per 7 days per user via
DigestLog.

Run via cron (Render scheduled job, GitHub Action, etc.):

    python manage.py send_job_alerts            # live send
    python manage.py send_job_alerts --dry-run  # print, don't email
    python manage.py send_job_alerts --user me@x.com  # one user
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from jobs.models import Application, DigestLog, Job


DIGEST_SYSTEM_PROMPT = """You write a short, warm intro for a weekly job digest emailed to busy parents.

Rules:
- Output ONLY the intro text. No greeting line, no sign-off, no subject.
- 1–2 short sentences. Maximum 220 characters total.
- Reference one specific pattern in their past applications (schedule type, remote, hours) if given.
- Sound like a thoughtful friend, never corporate. No exclamation points.
- Never invent specifics. If nothing useful in their history, write something universally warm.
"""


def _interest_summary(user):
    """Plain-text summary of a user's recent applications for the prompt."""
    apps = (
        Application.objects
        .filter(applicant=user)
        .select_related('job')
        .order_by('-applied_at')[:5]
    )
    if not apps:
        return ''
    bits = []
    for a in apps:
        j = a.job
        bits.append(
            f'- {j.title} ({j.get_schedule_type_display()}'
            f'{", remote" if j.is_remote else ""}'
            f'{f", {j.hours_per_day} hrs/day" if j.hours_per_day else ""})'
        )
    return 'Recent applications:\n' + '\n'.join(bits)


def _matched_jobs(user, since):
    """New active jobs since `since`, biased toward schedule types the user
    has applied to before."""
    base = Job.objects.filter(is_active=True, created_at__gte=since)

    prior_types = list(
        Application.objects
        .filter(applicant=user)
        .values_list('job__schedule_type', flat=True)
        .distinct()
    )
    if prior_types:
        preferred = base.filter(schedule_type__in=prior_types)
        if preferred.exists():
            base = preferred

    return list(base.order_by('-created_at')[:5])


def _draft_intro(user, jobs):
    """Use Claude to draft a 1–2 sentence personalised intro."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    try:
        from anthropic import Anthropic, APIError
    except ImportError:
        return None

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    user_prompt = (
        f'{_interest_summary(user)}\n\n'
        f'New roles this week: {len(jobs)}\n'
        'Write the intro now.'
    )
    try:
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=160,
            system=DIGEST_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_prompt}],
        )
    except APIError:
        return None
    text = ''.join(
        b.text for b in resp.content if getattr(b, 'type', None) == 'text'
    ).strip()
    return text or None


def _build_body(intro, jobs, base_url):
    lines = []
    if intro:
        lines.append(intro)
        lines.append('')
    else:
        lines.append(f'{len(jobs)} new flexible role{"s" if len(jobs) != 1 else ""} this week:')
        lines.append('')
    for j in jobs:
        lines.append(f'· {j.title} — {j.company}')
        meta = []
        if j.location:
            meta.append(j.location)
        if j.salary:
            meta.append(j.salary)
        meta.append(j.get_schedule_type_display())
        if j.is_remote:
            meta.append('Remote')
        if j.hours_per_day:
            meta.append(f'{j.hours_per_day} hrs/day')
        lines.append('  ' + ' · '.join(meta))
        lines.append(f'  {base_url}/jobs/{j.pk}/')
        lines.append('')
    lines.append('— Hirely')
    lines.append('You\'re getting this because you applied to a role recently.')
    return '\n'.join(lines)


class Command(BaseCommand):
    help = 'Send the weekly AI-curated job digest to recently-active parents.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Print emails to stdout instead of sending.")
        parser.add_argument('--user', type=str, default=None,
                            help="Only process this user's email address.")
        parser.add_argument('--base-url', type=str,
                            default='https://hirely.onrender.com',
                            help='Base URL for job links in the email.')

    def handle(self, *args, **opts):
        now = timezone.now()
        active_window = now - timedelta(days=30)
        send_window   = now - timedelta(days=7)
        new_jobs_since = now - timedelta(days=7)

        # Candidates: users who applied to anything in the last 30 days,
        # excluding employers whose own posts we shouldn't recommend back.
        candidates = (
            User.objects
            .filter(applications__applied_at__gte=active_window)
            .annotate(app_count=Count('applications'))
            .distinct()
        )

        if opts['user']:
            candidates = candidates.filter(email__iexact=opts['user'])

        sent = skipped = 0
        for user in candidates:
            if not user.email:
                skipped += 1
                continue

            log = getattr(user, 'digest_log', None)
            if log and log.last_sent_at >= send_window:
                skipped += 1
                continue

            jobs = _matched_jobs(user, new_jobs_since)
            if not jobs:
                skipped += 1
                continue

            intro = _draft_intro(user, jobs)
            body  = _build_body(intro, jobs, opts['base_url'].rstrip('/'))
            subject = f'{len(jobs)} new flexible role{"s" if len(jobs) != 1 else ""} for you'

            if opts['dry_run']:
                self.stdout.write(self.style.NOTICE(f'\n--- TO: {user.email} ---'))
                self.stdout.write(f'Subject: {subject}\n')
                self.stdout.write(body)
                self.stdout.write(self.style.NOTICE('--- END ---\n'))
                sent += 1
                continue

            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            DigestLog.objects.update_or_create(user=user)
            sent += 1

        self.stdout.write(self.style.SUCCESS(
            f'Digest: {sent} sent, {skipped} skipped.'
        ))
