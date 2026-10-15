import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.associations.models import Association


def private_member_photo_path(instance, filename):
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webp"
    return f"member-photos/{instance.association_id}/{uuid.uuid4()}.{suffix}"


def private_member_import_path(instance, filename):
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"member-imports/{instance.association_id}/{uuid.uuid4()}.{suffix}"


class LocalizedNameMixin:
    """Nombre en el idioma activo (es, ca, en) con el castellano de respaldo."""

    @property
    def label(self):
        language = (get_language() or settings.LANGUAGE_CODE).split("-")[0]
        return getattr(self, f"name_{language}", "") or self.name


class Section(LocalizedNameMixin, models.Model):
    """Cuerda común a todas las asociaciones (decisión 0012). Catálogo fijo."""

    code = models.SlugField(_("código"), max_length=40, unique=True)
    name = models.CharField(_("nombre"), max_length=80)
    name_ca = models.CharField(_("nombre en valenciano"), max_length=80, blank=True)
    name_en = models.CharField(_("nombre en inglés"), max_length=80, blank=True)
    order = models.PositiveSmallIntegerField(_("orden"), default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = _("cuerda")
        verbose_name_plural = _("cuerdas")

    def __str__(self):
        return self.label


class Instrument(LocalizedNameMixin, models.Model):
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="instruments", verbose_name=_("asociación")
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="instruments",
        null=True,
        blank=True,
        verbose_name=_("cuerda"),
    )
    # Código del catálogo predefinido (`apps/members/catalog.py`); vacío en
    # los instrumentos propios de la banda.
    code = models.SlugField(_("código del catálogo"), max_length=40, blank=True)
    name = models.CharField(_("nombre"), max_length=80)
    name_ca = models.CharField(_("nombre en valenciano"), max_length=80, blank=True)
    name_en = models.CharField(_("nombre en inglés"), max_length=80, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["association", "name"], name="unique_instrument_name"),
            models.UniqueConstraint(
                fields=["association", "code"], condition=~models.Q(code=""), name="unique_instrument_code"
            ),
        ]
        verbose_name = _("instrumento")
        verbose_name_plural = _("instrumentos")

    def __str__(self):
        return self.label


class Member(models.Model):
    class Kind(models.TextChoices):
        MUSICIAN = "musician", _("Músico socio")
        SUPPORTER = "supporter", _("Socio colaborador/mecenas")
        EXTERNAL = "external", _("Colaborador musical externo")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Activo")
        INACTIVE = "inactive", _("Inactivo")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="members", verbose_name=_("asociación")
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="member_profiles",
        null=True,
        blank=True,
        verbose_name=_("cuenta"),
    )
    external_id = models.CharField(_("identificador externo"), max_length=80, blank=True)
    first_name = models.CharField(_("nombre"), max_length=120)
    last_name = models.CharField(_("apellidos"), max_length=180)
    national_id = models.CharField(_("DNI/NIE"), max_length=40, blank=True)
    address = models.TextField(_("dirección"), blank=True)
    phone = models.CharField(_("teléfono"), max_length=40, blank=True)
    email = models.EmailField(_("correo electrónico"), blank=True)
    kind = models.CharField(_("tipo"), max_length=16, choices=Kind.choices, default=Kind.MUSICIAN)
    status = models.CharField(_("estado"), max_length=16, choices=Status.choices, default=Status.ACTIVE)
    photo = models.ImageField(_("foto"), upload_to=private_member_photo_path, blank=True)
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)
    updated_at = models.DateTimeField(_("fecha de actualización"), auto_now=True)
    # Trazabilidad minima (decision 0009): quien creo la ficha, quien la toco
    # por ultima vez y quien cambio su estado. Las importaciones dejan su rastro
    # en el lote, no aqui.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
        verbose_name=_("creada por"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
        verbose_name=_("actualizada por"),
    )
    status_changed_at = models.DateTimeField(_("fecha del cambio de estado"), null=True, blank=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
        verbose_name=_("estado cambiado por"),
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(fields=["association", "external_id"], condition=~models.Q(external_id=""), name="unique_member_external_id"),
            models.UniqueConstraint(fields=["association", "account"], condition=models.Q(account__isnull=False), name="unique_account_profile_per_association"),
        ]
        indexes = [models.Index(fields=["association", "status", "last_name"])]
        verbose_name = _("miembro")
        verbose_name_plural = _("miembros")

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class MemberInstrument(models.Model):
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="member_instruments", verbose_name=_("miembro")
    )
    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.PROTECT,
        related_name="member_instruments",
        verbose_name=_("instrumento"),
    )
    is_primary = models.BooleanField(_("principal"), default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["member", "instrument"], name="unique_member_instrument"),
            models.UniqueConstraint(fields=["member"], condition=models.Q(is_primary=True), name="one_primary_instrument_per_member"),
        ]
        verbose_name = _("instrumento de miembro")
        verbose_name_plural = _("instrumentos de miembros")

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.member.association_id != self.instrument.association_id:
            raise ValidationError({"instrument": _("El instrumento pertenece a otra asociación.")})


class MemberPosition(models.Model):
    """Cargo registrable de la ficha (ANALISIS.md 2). No concede ningún permiso."""

    class Position(models.TextChoices):
        PRESIDENT = "president", _("Presidencia")
        VICE_PRESIDENT = "vice_president", _("Vicepresidencia")
        SECRETARY = "secretary", _("Secretaría")
        TREASURER = "treasurer", _("Tesorería")
        CONTRACTOR = "contractor", _("Contratista")
        BOARD_MEMBER = "board_member", _("Vocalía")

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="positions", verbose_name=_("miembro")
    )
    position = models.CharField(_("cargo"), max_length=24, choices=Position.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["member", "position"], name="unique_member_position")]
        verbose_name = _("cargo de miembro")
        verbose_name_plural = _("cargos de miembros")

    def __str__(self):
        return self.get_position_display()


class ImportBatch(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", _("Subido")
        PREVIEW = "preview", _("Previsualización")
        CONFIRMED = "confirmed", _("Confirmada")
        FAILED = "failed", _("Fallida")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="member_imports", verbose_name=_("asociación")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="member_imports",
        verbose_name=_("creado por"),
    )
    filename = models.CharField(_("nombre de archivo"), max_length=255)
    content_hash = models.CharField(_("huella del contenido"), max_length=64)
    source_file = models.FileField(
        _("fichero original temporal"), upload_to=private_member_import_path, blank=True
    )
    source_headers = models.JSONField(_("columnas de origen"), default=list)
    status = models.CharField(_("estado"), max_length=16, choices=Status.choices, default=Status.UPLOADED)
    mapping = models.JSONField(_("asignación de columnas"), default=dict)
    preview = models.JSONField(_("previsualización"), default=list)
    result = models.JSONField(_("resultado"), default=dict)
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)
    confirmed_at = models.DateTimeField(_("fecha de confirmación"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["association", "content_hash"], name="unique_import_file_per_association")]
        verbose_name = _("lote de importación")
        verbose_name_plural = _("lotes de importación")
