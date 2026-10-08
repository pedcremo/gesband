import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Association(models.Model):
    class VisualStyle(models.TextChoices):
        # Estilos elegidos el 08/10/2026 sobre el lienzo de propuestas; `escenario` es el de Gesband.
        ESCENARIO = "escenario", _("Escenario")
        PARTITURA = "partitura", _("Partitura")
        FESTA = "festa", _("Festa")

    class ColorMode(models.TextChoices):
        SYSTEM = "system", _("Según el dispositivo")
        LIGHT = "light", _("Claro")
        DARK = "dark", _("Oscuro")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("nombre"), max_length=180)
    slug = models.SlugField(_("identificador para URL"), max_length=80, unique=True)
    logo = models.ImageField(_("logotipo"), upload_to="association-logos/%Y/%m/", blank=True)
    primary_color = models.CharField(
        _("color principal"),
        max_length=7,
        default="#1B4965",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", _("Usa un color hexadecimal, por ejemplo #1B4965."))],
    )
    secondary_color = models.CharField(
        _("color secundario"),
        max_length=7,
        default="#CAE9FF",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", _("Usa un color hexadecimal, por ejemplo #CAE9FF."))],
    )
    motto = models.CharField(_("lema"), max_length=240, blank=True)
    visual_style = models.CharField(
        _("estilo visual"), max_length=16, choices=VisualStyle.choices, default=VisualStyle.ESCENARIO
    )
    color_mode = models.CharField(_("modo de color"), max_length=8, choices=ColorMode.choices, default=ColorMode.SYSTEM)
    timezone = models.CharField(_("zona horaria"), max_length=64, default="Europe/Madrid")
    is_active = models.BooleanField(_("activa"), default=True)
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("asociación")
        verbose_name_plural = _("asociaciones")

    def __str__(self):
        return self.name


class AssociationAccess(models.Model):
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="accesses", verbose_name=_("asociación")
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="association_accesses",
        verbose_name=_("cuenta"),
    )
    is_active = models.BooleanField(_("activo"), default=True)
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["association", "account"], name="unique_association_access")]
        verbose_name = _("acceso a asociación")
        verbose_name_plural = _("accesos a asociaciones")

    def __str__(self):
        return f"{self.account} @ {self.association}"


class AssociationRole(models.Model):
    class Role(models.TextChoices):
        MEMBER = "member", _("Músico")
        BOARD = "board", _("Junta")
        ORGANIZER = "organizer", _("Contratista/organización")
        DIRECTOR = "director", _("Dirección musical")
        ADMIN = "admin", _("Administración")
        PLATFORM = "platform", _("Administración de plataforma")
        WEB_EDITOR = "web_editor", _("Edición web")

    access = models.ForeignKey(
        AssociationAccess,
        on_delete=models.CASCADE,
        related_name="role_assignments",
        verbose_name=_("acceso"),
    )
    role = models.CharField(_("rol"), max_length=24, choices=Role.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["access", "role"], name="unique_role_per_access")]
        verbose_name = _("rol de asociación")
        verbose_name_plural = _("roles de asociación")

    def __str__(self):
        return f"{self.access}: {self.get_role_display()}"
