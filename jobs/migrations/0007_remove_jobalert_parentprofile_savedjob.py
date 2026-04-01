from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0006_job_respond_by_job_salary_max_job_salary_min_and_more'),
    ]

    operations = [
        # Remove models that reference Job first (FK constraint order)
        migrations.DeleteModel(
            name='SavedJob',
        ),
        migrations.DeleteModel(
            name='JobAlert',
        ),
        migrations.DeleteModel(
            name='ParentProfile',
        ),
        # Remove fields added in 0006 that no longer exist in models.py
        migrations.RemoveField(
            model_name='job',
            name='respond_by',
        ),
        migrations.RemoveField(
            model_name='job',
            name='salary_max',
        ),
        migrations.RemoveField(
            model_name='job',
            name='salary_min',
        ),
    ]
