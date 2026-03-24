from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_application_resume'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='cover_letter',
            field=models.TextField(blank=True, default=''),
        ),
    ]
