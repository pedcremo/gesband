from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("activities", "0003_alter_activity_options_alter_attendance_options_and_more")]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="is_mandatory",
            field=models.BooleanField(default=False, verbose_name="asistencia obligatoria"),
        ),
    ]
