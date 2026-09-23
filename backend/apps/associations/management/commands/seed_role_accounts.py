"""Crea una cuenta sintética por rol para probar el MVP desde cada situación.

Uso previsto: entornos locales y de prueba. Las cuentas no son superusuarias, de
modo que ejercitan de verdad las comprobaciones de rol del servidor.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.activities.models import Activity, Invitation
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members.models import Member

# Dominios reservados por la IANA: ninguna dirección de estas cuentas puede
# corresponder a una persona real ni recibir correo.
RESERVED_DOMAINS = ("invalid", "test", "example", "localhost")

DEFAULT_PASSWORD = "Gesband.demo.2026"

# Un perfil por rol del modelo, con nombres claramente ficticios.
ROLE_PROFILES = [
    (AssociationRole.Role.MEMBER, "Prova", "Músic"),
    (AssociationRole.Role.BOARD, "Prova", "Junta"),
    (AssociationRole.Role.ORGANIZER, "Prova", "Contractista"),
    (AssociationRole.Role.DIRECTOR, "Prova", "Direcció"),
    (AssociationRole.Role.ADMIN, "Prova", "Administració"),
    (AssociationRole.Role.PLATFORM, "Prova", "Plataforma"),
    (AssociationRole.Role.WEB_EDITOR, "Prova", "Web"),
]


class Command(BaseCommand):
    help = "Crea o actualiza una cuenta de prueba por cada rol de una asociación."

    def add_arguments(self, parser):
        parser.add_argument(
            "--association",
            dest="association",
            help="Slug de la asociación. Obligatorio si hay más de una activa.",
        )
        parser.add_argument(
            "--domain",
            default="gesband.invalid",
            help="Dominio de correo de las cuentas. Debe ser un dominio reservado.",
        )
        parser.add_argument(
            "--prefix",
            default="prova",
            help="Prefijo del nombre de usuario y del correo.",
        )
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Contraseña de las cuentas nuevas.",
        )
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Restablece también la contraseña de las cuentas ya existentes.",
        )
        parser.add_argument(
            "--no-invite",
            action="store_true",
            help="No convoca las fichas de prueba a las actividades publicadas futuras.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Permite ejecutarlo con DEBUG desactivado.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Este comando siembra datos de prueba. Con DEBUG desactivado requiere --force."
            )

        domain = options["domain"].strip().lower().lstrip("@")
        if domain.rsplit(".", 1)[-1] not in RESERVED_DOMAINS:
            raise CommandError(
                "El dominio debe terminar en un TLD reservado "
                f"({', '.join('.' + item for item in RESERVED_DOMAINS)}) para no escribir a personas reales."
            )

        association = self._association(options["association"])
        password = options["password"]
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError("La contraseña no cumple las reglas: " + " ".join(exc.messages)) from exc

        prefix = options["prefix"].strip().lower()
        account_model = get_user_model()
        rows = []

        with transaction.atomic():
            for role, first_name, last_name in ROLE_PROFILES:
                username = f"{prefix}-{role}"
                email = f"{prefix}-{role}@{domain}"
                account, account_created = account_model.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_active": True,
                        "is_staff": False,
                        "is_superuser": False,
                    },
                )
                if account_created or options["reset_password"]:
                    account.set_password(password)
                    account.save(update_fields=["password"])

                access, _ = AssociationAccess.objects.get_or_create(
                    association=association, account=account, defaults={"is_active": True}
                )
                if not access.is_active:
                    access.is_active = True
                    access.save(update_fields=["is_active"])

                # Un rol por cuenta: así cada situación se observa aislada.
                AssociationRole.objects.get_or_create(access=access, role=role)

                member, member_created = Member.objects.get_or_create(
                    association=association,
                    external_id=f"DEMO-{role.upper()}",
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "kind": Member.Kind.MUSICIAN,
                        "status": Member.Status.ACTIVE,
                    },
                )
                if member.account_id != account.pk:
                    member.account = account
                    member.save(update_fields=["account", "updated_at"])

                rows.append(
                    {
                        "role": role,
                        "username": username,
                        "email": email,
                        "account_created": account_created,
                        "member_created": member_created,
                        "member": member,
                    }
                )

            invited = 0
            if not options["no_invite"]:
                upcoming = Activity.objects.filter(
                    association=association,
                    status=Activity.Status.PUBLISHED,
                    starts_at__gte=timezone.now(),
                )
                for activity in upcoming:
                    for row in rows:
                        _, created = Invitation.objects.get_or_create(
                            activity=activity,
                            member=row["member"],
                            defaults={"activity_version": activity.version},
                        )
                        invited += int(created)

        self.stdout.write(self.style.SUCCESS(f"Asociación: {association.name} ({association.slug})"))
        self.stdout.write(f"Contraseña de las cuentas nuevas: {password}")
        self.stdout.write("")
        self.stdout.write(f"{'Rol':<12} {'Usuario':<22} {'Correo':<36} Estado")
        for row in rows:
            state = "creada" if row["account_created"] else "ya existía"
            self.stdout.write(f"{row['role']:<12} {row['username']:<22} {row['email']:<36} {state}")
        self.stdout.write("")
        self.stdout.write(f"Convocatorias añadidas a actividades publicadas futuras: {invited}")

    def _association(self, slug):
        if slug:
            try:
                return Association.objects.get(slug=slug, is_active=True)
            except Association.DoesNotExist as exc:
                raise CommandError(f"No hay ninguna asociación activa con el slug «{slug}».") from exc
        candidates = list(Association.objects.filter(is_active=True)[:2])
        if not candidates:
            raise CommandError("No hay ninguna asociación activa. Crea una antes de sembrar cuentas.")
        if len(candidates) > 1:
            raise CommandError("Hay varias asociaciones activas: indica --association <slug>.")
        return candidates[0]
