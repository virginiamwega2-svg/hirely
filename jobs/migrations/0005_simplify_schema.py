"""
Migration 0005 — Simplify schema for MVP
─────────────────────────────────────────
Changes applied:

Job model
  - job_type          → renamed to schedule_type
  - SCHEDULE_CHOICES  → collapsed from 6 to 3 (fixed / flexible / anytime)
  - hours_per_week    → removed (free-text CharField, unfiltered)
  - hours_per_day     → added   (PositiveSmallIntegerField, filterable)
  - updated_at        → added   (auto_now timestamp)
  - location          → blank=True (async/remote roles don't need one)
  - requirements      → blank=True (optional for simple postings)
  - is_active         → db_index=True
  - is_remote         → db_index=True

Application model
  - cover_letter      → removed (always blank, never read)
  - status 'reviewed' → migrated to 'seen' (clearer label)

Data migration
  - Existing schedule values mapped to new 3-choice set:
      school_hours / term_time / evenings_weekends  → fixed
      flexible / job_share                          → flexible
      freelance / full_time / part_time / remote
      / contract / internship                       → anytime or flexible
"""

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


# ── Data migration helpers ────────────────────────────────────────────

OLD_TO_NEW = {
    'school_hours':      'fixed',
    'term_time':         'fixed',
    'evenings_weekends': 'fixed',
    'flexible':          'flexible',
    'job_share':         'flexible',
    'freelance':         'anytime',
    # values that may exist from the very first migration
    'full_time':         'fixed',
    'part_time':         'flexible',
    'remote':            'anytime',
    'contract':          'flexible',
    'internship':        'flexible',
}


def migrate_schedule_types(apps, schema_editor):
    """Map old multi-choice values to the clean 3-choice set."""
    Job = apps.get_model('jobs', 'Job')
    for job in Job.objects.all():
        job.schedule_type = OLD_TO_NEW.get(job.schedule_type, 'flexible')
        job.save(update_fields=['schedule_type'])


def migrate_status_reviewed_to_seen(apps, schema_editor):
    """'reviewed' was ambiguous — rename to 'seen'."""
    Application = apps.get_model('jobs', 'Application')
    Application.objects.filter(status='reviewed').update(status='seen')


def reverse_schedule_types(apps, schema_editor):
    """Reverse: map everything back to 'flexible' (best-effort)."""
    Job = apps.get_model('jobs', 'Job')
    Job.objects.all().update(schedule_type='flexible')


def reverse_status(apps, schema_editor):
    Application = apps.get_model('jobs', 'Application')
    Application.objects.filter(status='seen').update(status='reviewed')


# ── Migration ─────────────────────────────────────────────────────────

class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0004_job_flexibility_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # 1. Rename job_type → schedule_type (preserves all existing data)
        migrations.RenameField(
            model_name='job',
            old_name='job_type',
            new_name='schedule_type',
        ),

        # 2. Update schedule_type: new choices + db_index + verbose_name
        migrations.AlterField(
            model_name='job',
            name='schedule_type',
            field=models.CharField(
                choices=[
                    ('fixed',    'Fixed Schedule'),
                    ('flexible', 'Flexible Hours'),
                    ('anytime',  'Async — Work Any Time'),
                ],
                default='flexible',
                db_index=True,
                max_length=20,
                verbose_name='Schedule Type',
            ),
        ),

        # 3. Drop hours_per_week (free-text, unfiltered)
        migrations.RemoveField(
            model_name='job',
            name='hours_per_week',
        ),

        # 4. Add hours_per_day (integer, filterable, validated 1–12)
        migrations.AddField(
            model_name='job',
            name='hours_per_day',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name='Hours per Day',
                help_text='Typical hours per working day (1–12). Leave blank if it varies.',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(12),
                ],
            ),
        ),

        # 5. Add updated_at timestamp
        migrations.AddField(
            model_name='job',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),

        # 6. location → optional (remote/async roles don't always have one)
        migrations.AlterField(
            model_name='job',
            name='location',
            field=models.CharField(
                blank=True,
                max_length=200,
                help_text='Leave blank for fully remote / location-independent roles.',
            ),
        ),

        # 7. requirements → optional
        migrations.AlterField(
            model_name='job',
            name='requirements',
            field=models.TextField(
                blank=True,
                verbose_name='What Applicants Will Need',
                help_text='Optional — leave blank if there are no specific requirements.',
            ),
        ),

        # 8. is_active → add db_index
        migrations.AlterField(
            model_name='job',
            name='is_active',
            field=models.BooleanField(default=True, db_index=True),
        ),

        # 9. is_remote → add db_index
        migrations.AlterField(
            model_name='job',
            name='is_remote',
            field=models.BooleanField(
                default=False,
                db_index=True,
                verbose_name='Remote / Work from Home',
            ),
        ),

        # 10. Map old schedule values to the new 3-choice set
        migrations.RunPython(migrate_schedule_types, reverse_code=reverse_schedule_types),

        # 11. Drop cover_letter from Application (always blank, never used)
        migrations.RemoveField(
            model_name='application',
            name='cover_letter',
        ),

        # 12. Update status choices: 'reviewed' → 'seen'
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending',  'Pending'),
                    ('seen',     'Seen'),
                    ('accepted', 'Accepted'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
                max_length=20,
            ),
        ),

        # 13. Migrate any existing 'reviewed' rows to 'seen'
        migrations.RunPython(migrate_status_reviewed_to_seen, reverse_code=reverse_status),
    ]
