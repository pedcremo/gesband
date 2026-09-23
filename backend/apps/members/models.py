import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.associations.models import Association


def private_member_photo_path(instance, filename):
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webp"
    return f"member-photos/{instance.association_id}/{uuid.uuid4()}.{suffix}"


def private_member_import_path(instance, filename):
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"member-imports/{instance.association_id}/{uuid.uuid4()}.{suffix}"


class Section(models.Model):
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="sections", verbose_name=_("asociación")
    )
    name = models.CharField(_("nombre"), max_length=80)
    order = models.PositiveSmallIntegerField(_("orden"), default=0)

    class Meta:
        ordering = ["order", "name"]
        constraints = [models.UniqueConstraint(fields=["association", "name"], name="unique_section_name")]
        verbose_name = _("cuerda")
        verbose_name_plural = _("cuerdas")

    def __str__(self):
        return self.name


class Instrument(models.Model):
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
    name = models.CharField(_("nombre"), max_length=80)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["association", "name"], name="unique_instrument_name")]
        verbose_name = _("instrumento")
        verbose_name_plural = _("instrumentos")

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.section_id and self.section.association_id != self.association_id:
            raise ValidationError({"section": _("La cuerda pertenece a otra asociación.")})

    def __str__(self):
        return self.name


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
