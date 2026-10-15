from django.db import migrations, models


class Migration(migrations.Migration):
    """Las cuerdas ya no pertenecen a ninguna asociación (decisión 0012)."""

    dependencies = [
        ("members", "0006_global_sections_data"),
    ]

    operations = [
        migrations.RemoveField(model_name="section", name="association"),
        migrations.AlterField(
            model_name="section",
            name="code",
            field=models.SlugField(max_length=40, unique=True, verbose_name="código"),
        ),
        migrations.AddConstraint(
            model_name="instrument",
            constraint=models.UniqueConstraint(
                condition=models.Q(("code", ""), _negated=True),
                fields=("association", "code"),
                name="unique_instrument_code",
            ),
        ),
    ]
