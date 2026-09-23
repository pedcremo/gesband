import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_account_options_alter_account_email"),
        ("associations", "0002_alter_association_options_and_more"),
        ("members", "0003_importbatch_source_file_importbatch_source_headers_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessInvitation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name="identificador")),
                ("email", models.EmailField(max_length=254, verbose_name="correo electrónico")),
                ("token_digest", models.CharField(max_length=64, unique=True, verbose_name="huella del token")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="fecha de creación")),
                ("expires_at", models.DateTimeField(verbose_name="fecha de caducidad")),
                ("sent_at", models.DateTimeField(blank=True, null=True, verbose_name="fecha de envío")),
                ("accepted_at", models.DateTimeField(blank=True, null=True, verbose_name="fecha de aceptación")),
                ("revoked_at", models.DateTimeField(blank=True, null=True, verbose_name="fecha de revocación")),
                ("last_send_error", models.TextField(blank=True, verbose_name="último error de envío")),
                ("association", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_invitations", to="associations.association", verbose_name="asociación")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_access_invitations", to=settings.AUTH_USER_MODEL, verbose_name="creada por")),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_invitations", to="members.member", verbose_name="miembro")),
                ("revoked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="revoked_access_invitations", to=settings.AUTH_USER_MODEL, verbose_name="revocada por")),
            ],
            options={
                "verbose_name": "invitación de acceso",
                "verbose_name_plural": "invitaciones de acceso",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["association", "email", "created_at"], name="accounts_ac_associa_dfc729_idx")],
                "constraints": [models.UniqueConstraint(condition=models.Q(("accepted_at__isnull", True), ("revoked_at__isnull", True)), fields=("member",), name="unique_open_access_invitation_per_member")],
            },
        ),
    ]
