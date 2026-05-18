from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


class Job(models.Model):
    """
    MVP schema — three tables only: User (built-in), Job, Application.

    Schedule is the core concept. Three mutually exclusive patterns:
      fixed    — employer sets specific days/hours (e.g. Mon–Wed 9–3)
      flexible — total hours are agreed but parent chooses when
      anytime  — fully async, no required hours; work any time
    """

    SCHEDULE_CHOICES = [
        ('fixed',    'Fixed Schedule'),
        ('flexible', 'Flexible Hours'),
        ('anytime',  'Async — Work Any Time'),
    ]

    # ── Core identity ────────────────────────────────────────────────
    title    = models.CharField(max_length=200)
    company  = models.CharField(max_length=200)
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text='Leave blank for fully remote / location-independent roles.',
    )

    # ── Flexibility fields — the whole point of the platform ─────────
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_CHOICES,
        default='flexible',
        db_index=True,
        verbose_name='Schedule Type',
    )
    hours_per_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name='Hours per Day',
        help_text='Typical hours per working day (1–12). Leave blank if it varies.',
    )
    is_remote = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Remote / Work from Home',
    )

    # ── Role content ─────────────────────────────────────────────────
    description  = models.TextField(verbose_name='About This Role')
    requirements = models.TextField(
        blank=True,
        verbose_name='What Applicants Will Need',
        help_text='Optional — leave blank if there are no specific requirements.',
    )
    salary = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Pay Rate',
        help_text='e.g. "$15/hr", "€18/hr", "₹30,000/month". Leave blank if negotiable.',
    )

    # ── Ownership & lifecycle ────────────────────────────────────────
    posted_by  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} at {self.company}'

    # ── Derived flex signals (no extra DB columns needed) ────────────

    @property
    def flex_score(self):
        """
        Integer 1–3.  Derived entirely from schedule_type + is_remote
        so it never goes stale and needs no maintenance.

          anytime  + remote  = 3  (fully async, no location)
          anytime  + on-site = 2  (async but location-dependent)
          flexible + remote  = 3  (choose hours, no commute)
          flexible + on-site = 2  (choose hours, need to go in)
          fixed    + remote  = 2  (set hours, no commute)
          fixed    + on-site = 1  (set hours + commute — least flexible)
        """
        score = 1 if self.schedule_type == 'fixed' else 0
        if self.schedule_type == 'anytime':
            score += 2
        elif self.schedule_type == 'flexible':
            score += 1
        if self.is_remote:
            score += 1
        return min(score, 3)

    @property
    def flex_label(self):
        return {1: 'Some Flex', 2: 'Flexible', 3: 'Very Flexible'}.get(self.flex_score, '')

    @property
    def flex_colour(self):
        return {1: 'secondary', 2: 'primary', 3: 'success'}.get(self.flex_score, 'secondary')

    @property
    def is_new(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).total_seconds() < 172800  # 48 hours


class Application(models.Model):
    """
    Minimal — just enough to connect a parent to a job and let the
    employer know someone applied.  No cover letter (removed).
    Status is employer-managed; most MVPs will leave everything on
    'pending' and handle it via email.
    """

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('seen',     'Seen'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    SUGGESTION_CHOICES = [
        ('shortlist', 'Shortlist'),
        ('hold',      'Hold'),
        ('decline',   'Decline'),
    ]

    job       = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    resume    = models.FileField(upload_to='resumes/', blank=True, null=True)
    note      = models.CharField(
        max_length=400,
        blank=True,
        verbose_name='Personal Note',
        help_text='Optional 1–2 sentence intro — kept short on purpose.',
    )
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    # AI-generated, cached so each summary costs at most one call.
    ai_summary    = models.CharField(max_length=400, blank=True)
    ai_suggestion = models.CharField(max_length=20, blank=True, choices=SUGGESTION_CHOICES)

    class Meta:
        ordering = ['-applied_at']
        unique_together = ('job', 'applicant')

    def __str__(self):
        return f'{self.applicant.email} → {self.job.title}'


class ParentProfile(models.Model):
    """
    AI-extracted structured summary of a parent's CV.

    Built automatically from the most recent uploaded resume by the
    resume_parser. Powers job matching, smarter chat answers, and
    better personalisation in the weekly digest.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')

    # Plain-text extraction — keeps the source for re-runs if the prompt evolves.
    raw_resume_text = models.TextField(blank=True)

    # AI-extracted structured fields. All optional — Claude returns "" when unsure.
    years_experience      = models.PositiveSmallIntegerField(null=True, blank=True)
    top_skills            = models.CharField(max_length=400, blank=True,
                                             help_text='Comma-separated, max 6.')
    location_hint         = models.CharField(max_length=120, blank=True)
    schedule_preference   = models.CharField(max_length=120, blank=True,
                                             help_text='Free-text hint: "mornings", "term-time", etc.')
    summary               = models.CharField(max_length=400, blank=True,
                                             help_text='1–2 sentence parent-friendly bio.')

    parsed_at = models.DateTimeField(auto_now=True)
    parse_failed = models.BooleanField(default=False)

    def __str__(self):
        return f'Profile for {self.user.email}'

    @property
    def skill_list(self):
        return [s.strip() for s in self.top_skills.split(',') if s.strip()]


class DigestLog(models.Model):
    """
    Throttle record for the weekly AI-curated job digest.
    One row per user; updated each time we send their digest.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='digest_log')
    last_sent_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Digest for {self.user.email} @ {self.last_sent_at:%Y-%m-%d}'


class DigestOptOut(models.Model):
    """Parent has clicked unsubscribe — never send the weekly digest to them."""
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='digest_opt_out')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.email} opted out'


class SavedJob(models.Model):
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    job      = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')
        ordering = ['-saved_at']

    def __str__(self):
        return f'{self.user.email} saved {self.job.title}'
