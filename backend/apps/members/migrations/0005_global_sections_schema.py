from django.db import migrations, models


class Migration(migrations.Migration):
    """Primer paso hacia cuerdas comunes (decisión 0012): campos nuevos, aún tolerantes."""

    dependencies = [
        ("members", "0004_member_traceability_and_positions"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="section", name="unique_section_name"),
        migrations.AlterField(
            model_name="section",
            name="association",
            field=models.ForeignKey(
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="sections",
                to="associations.association",
                verbose_name="asociación",
            ),
        ),
        migrations.AddField(
            model_name="section",
            name="code",
            field=models.SlugField(max_length=40, null=True, verbose_name="código"),
        ),
        migrations.AddField(
            model_name="section",
            name="name_ca",
            field=models.CharField(blank=True, default="", max_length=80, verbose_name="nombre en valenciano"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="section",
            name="name_en",
            field=models.CharField(blank=True, default="", max_length=80, verbose_name="nombre en inglés"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="instrument",
            name="code",
            field=models.SlugField(blank=True, default="", max_length=40, verbose_name="código del catálogo"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="instrument",
            name="name_ca",
            field=models.CharField(blank=True, default="", max_length=80, verbose_name="nombre en valenciano"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="instrument",
            name="name_en",
            field=models.CharField(blank=True, default="", max_length=80, verbose_name="nombre en inglés"),
            preserve_default=False,
        ),
    ]
