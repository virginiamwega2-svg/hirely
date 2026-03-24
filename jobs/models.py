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
        help_text='e.g. "£15/hr", "£25,000 pro-rata". Leave blank if negotiable.',
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

    job       = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    resume    = models.FileField(upload_to='resumes/', blank=True, null=True)
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']
        unique_together = ('job', 'applicant')

    def __str__(self):
        return f'{self.applicant.email} → {self.job.title}'
