from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_application_cover_letter_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='job_type',
            field=models.CharField(
                choices=[
                    ('school_hours',      'School Hours (9am–3pm)'),
                    ('term_time',         'Term-Time Only'),
                    ('evenings_weekends', 'Evenings & Weekends'),
                    ('flexible',          'Flexible — You Choose Your Hours'),
                    ('job_share',         'Job Share'),
                    ('freelance',         'Freelance / Projects'),
                ],
                default='flexible',
                max_length=30,
                verbose_name='Schedule Type',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='hours_per_week',
            field=models.CharField(
                blank=True,
                max_length=50,
                verbose_name='Hours per Week',
                help_text='e.g. "10–20 hrs/week" or "Up to 25 hrs"',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='is_remote',
            field=models.BooleanField(
                default=False,
                verbose_name='Remote / Work from Home',
            ),
        ),
    ]
