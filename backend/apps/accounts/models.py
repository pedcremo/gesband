import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class Account(AbstractUser):
    email = models.EmailField(_("correo electrónico"), unique=True)

    class Meta(AbstractUser.Meta):
        verbose_name = _("cuenta")
        verbose_name_plural = _("cuentas")

    def __str__(self):
        return self.get_full_name() or self.email or self.username


class AccessInvitation(models.Model):
    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    association = models.ForeignKey(
        "associations.Association",
        on_delete=models.CASCADE,
        related_name="access_invitations",
        verbose_name=_("asociación"),
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.CASCADE,
        related_name="access_invitations",
        verbose_name=_("miembro"),
    )
    email = models.EmailField(_("correo electrónico"))
    token_digest = models.CharField(_("huella del token"), max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_access_invitations",
        verbose_name=_("creada por"),
    )
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="revoked_access_invitations",
        verbose_name=_("revocada por"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)
    expires_at = models.DateTimeField(_("fecha de caducidad"))
    sent_at = models.DateTimeField(_("fecha de envío"), null=True, blank=True)
    accepted_at = models.DateTimeField(_("fecha de aceptación"), null=True, blank=True)
    revoked_at = models.DateTimeField(_("fecha de revocación"), null=True, blank=True)
    last_send_error = models.TextField(_("último error de envío"), blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["member"],
                condition=models.Q(accepted_at__isnull=True, revoked_at__isnull=True),
                name="unique_open_access_invitation_per_member",
            )
        ]
        indexes = [models.Index(fields=["association", "email", "created_at"], name="accounts_ac_associa_dfc729_idx")]
        verbose_name = _("invitación de acceso")
        verbose_name_plural = _("invitaciones de acceso")

    def __str__(self):
        return f"{self.member} · {self.email}"
