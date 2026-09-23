import uuid
from django.conf import settings
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Association",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("logo", models.ImageField(blank=True, upload_to="association-logos/%Y/%m/")),
                ("primary_color", models.CharField(default="#1B4965", max_length=7, validators=[django.core.validators.RegexValidator("^#[0-9A-Fa-f]{6}$", "Usa un color hexadecimal, por ejemplo #1B4965.")])),
                ("secondary_color", models.CharField(default="#CAE9FF", max_length=7, validators=[django.core.validators.RegexValidator("^#[0-9A-Fa-f]{6}$", "Usa un color hexadecimal, por ejemplo #CAE9FF.")])),
                ("motto", models.CharField(blank=True, max_length=240)),
                ("timezone", models.CharField(default="Europe/Madrid", max_length=64)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AssociationAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("account", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="association_accesses", to=settings.AUTH_USER_MODEL)),
                ("association", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="accesses", to="associations.association")),
            ],
        ),
        migrations.CreateModel(
            name="AssociationRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("member", "Músico"), ("board", "Junta"), ("organizer", "Contratista/organización"), ("director", "Dirección musical"), ("admin", "Administración"), ("platform", "Administración de plataforma"), ("web_editor", "Edición web")], max_length=24)),
                ("access", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="role_assignments", to="associations.associationaccess")),
            ],
        ),
        migrations.AddConstraint(model_name="associationaccess", constraint=models.UniqueConstraint(fields=("association", "account"), name="unique_association_access")),
        migrations.AddConstraint(model_name="associationrole", constraint=models.UniqueConstraint(fields=("access", "role"), name="unique_role_per_access")),
    ]
