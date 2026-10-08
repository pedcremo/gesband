import hashlib
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.associations.models import AssociationAccess, AssociationRole
from apps.members.models import Member

from .models import AccessInvitation


def invitation_token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@transaction.atomic
def issue_access_invitation(*, member, created_by):
    locked_member = Member.objects.select_for_update().select_related("association").get(pk=member.pk)
    ensure_access_manager(created_by, locked_member.association)
    email = locked_member.email.strip().lower()
    if locked_member.status != Member.Status.ACTIVE:
        raise ValidationError(_("Solo se puede invitar a miembros activos."))
    if locked_member.account_id:
        raise ValidationError(_("Este miembro ya tiene una cuenta vinculada."))
    if not email:
        raise ValidationError(_("El miembro no tiene correo electrónico."))
    account_model = get_user_model()
    if account_model.objects.filter(email__iexact=email).exists():
        raise ValidationError(
            _("Ya existe una cuenta con este correo. Debe vincularse tras comprobar su identidad.")
        )

    now = timezone.now()
    AccessInvitation.objects.filter(
        member=locked_member,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=now, revoked_by=created_by)
    token = secrets.token_urlsafe(32)
    invitation = AccessInvitation.objects.create(
        association=locked_member.association,
        member=locked_member,
        email=email,
        token_digest=invitation_token_digest(token),
        created_by=created_by,
        expires_at=now + timedelta(hours=settings.ACCESS_INVITATION_TTL_HOURS),
    )
    return invitation, token


def deliver_access_invitation(*, invitation, token, activation_url):
    subject = _("Activa tu cuenta de Gesband")
    body = _(
        "Has recibido una invitación para acceder a %(association)s como %(member)s.\n\n"
        "Crea tu contraseña mediante este enlace, válido hasta %(expires)s:\n%(url)s\n\n"
        "Si no esperabas esta invitación, ignora el mensaje."
    ) % {
        "association": invitation.association.name,
        "member": invitation.member,
        "expires": timezone.localtime(invitation.expires_at).strftime("%d/%m/%Y %H:%M"),
        "url": activation_url,
    }
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [invitation.email], fail_silently=False)
    except Exception as exc:
        invitation.last_send_error = str(exc)[:2000]
        invitation.save(update_fields=["last_send_error"])
        return False
    invitation.sent_at = timezone.now()
    invitation.last_send_error = ""
    invitation.save(update_fields=["sent_at", "last_send_error"])
    return True


def invitation_for_token(token):
    if not token or len(token) > 256:
        return None
    return AccessInvitation.objects.select_related("association", "member").filter(
        token_digest=invitation_token_digest(token)
    ).first()


def invitation_is_usable(invitation):
    return bool(
        invitation
        and invitation.accepted_at is None
        and invitation.revoked_at is None
        and invitation.expires_at > timezone.now()
        and invitation.member.account_id is None
        and invitation.member.status == Member.Status.ACTIVE
        and invitation.member.association_id == invitation.association_id
        and invitation.member.email.strip().lower() == invitation.email
    )


@transaction.atomic
def activate_access_invitation(*, invitation_id, token, password):
    invitation = AccessInvitation.objects.select_for_update().select_related(
        "association", "member"
    ).get(pk=invitation_id)
    if not secrets.compare_digest(invitation.token_digest, invitation_token_digest(token)):
        raise ValidationError(_("La invitación no es válida."))
    if not invitation_is_usable(invitation):
        raise ValidationError(_("La invitación ha caducado o ya no está disponible."))

    member = Member.objects.select_for_update().get(pk=invitation.member_id)
    account_model = get_user_model()
    if account_model.objects.filter(email__iexact=invitation.email).exists():
        raise ValidationError(_("Ya existe una cuenta con este correo."))
    account = account_model(
        username=f"member-{uuid.uuid4().hex}",
        email=invitation.email,
        first_name=member.first_name[:150],
        last_name=member.last_name[:150],
        is_active=True,
    )
    validate_password(password, user=account)
    account.set_password(password)
    account.save()

    access, _created = AssociationAccess.objects.get_or_create(
        association=invitation.association,
        account=account,
        defaults={"is_active": True},
    )
    if not access.is_active:
        access.is_active = True
        access.save(update_fields=["is_active"])
    AssociationRole.objects.get_or_create(access=access, role=AssociationRole.Role.MEMBER)
    member.account = account
    member.save(update_fields=["account", "updated_at"])
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    return account


@transaction.atomic
def revoke_access_invitation(*, invitation, revoked_by):
    locked = AccessInvitation.objects.select_for_update().select_related("association").get(pk=invitation.pk)
    ensure_access_manager(revoked_by, locked.association)
    if locked.accepted_at is not None:
        raise ValidationError(_("Una invitación aceptada no se puede revocar."))
    if locked.revoked_at is None:
        locked.revoked_at = timezone.now()
        locked.revoked_by = revoked_by
        locked.save(update_fields=["revoked_at", "revoked_by"])
    return locked


# --- Accesos y roles desde el panel (decision 0009) --------------------------
#
# `board` y `admin` gestionan invitaciones, accesos y roles de su asociacion.
# Reglas que no dependen de la vista:
# - solo `admin` concede o quita `admin`, y solo `admin` toca el acceso de
#   quien es `admin`;
# - `platform` y `web_editor` no se asignan ni se quitan desde aqui;
# - nunca queda una asociacion sin ningun `admin` activo;
# - nadie desactiva su propio acceso;
# - las cuentas no se borran: la identidad puede pertenecer a otras asociaciones.


def ensure_access_manager(actor, association):
    """403 si la cuenta no gestiona accesos (`accounts.manage`) en esa asociación."""
    from apps.associations.permissions import ensure_permission

    ensure_permission(actor, association, "accounts.manage")


def _is_admin(actor, association):
    if actor.is_superuser:
        return True
    return AssociationRole.objects.filter(
        access__account=actor,
        access__association=association,
        access__is_active=True,
        role=AssociationRole.Role.ADMIN,
    ).exists()


def _lock_active_admins(association):
    """Accesos activos con `admin`, bloqueados para que dos bajas simultáneas
    no dejen la asociación sin nadie que la administre."""
    admin_access_ids = AssociationRole.objects.filter(
        access__association=association, role=AssociationRole.Role.ADMIN
    ).values_list("access_id", flat=True)
    return list(
        AssociationAccess.objects.select_for_update()
        .filter(pk__in=list(admin_access_ids), is_active=True, account__is_active=True)
        .values_list("pk", flat=True)
    )


def _lock_access(access, association):
    """El acceso, bloqueado y comprobado dentro de la asociación indicada."""
    try:
        return AssociationAccess.objects.select_for_update().select_related("account", "association").get(
            pk=access.pk, association=association
        )
    except AssociationAccess.DoesNotExist as exc:
        from django.http import Http404

        raise Http404(_("Ese acceso no pertenece a esta asociación.")) from exc


def _record(locked, actor, action, role=""):
    from .models import AccessChange

    AccessChange.objects.create(
        association=locked.association, access=locked, actor=actor, action=action, role=role
    )


def _ensure_assignable(role):
    from apps.associations.permissions import PANEL_ASSIGNABLE_ROLES

    if role not in AssociationRole.Role.values:
        raise ValidationError(_("Rol no válido."))
    if role not in PANEL_ASSIGNABLE_ROLES:
        raise ValidationError(_("Este rol lo asigna el operador de la plataforma, no la asociación."))


@transaction.atomic
def grant_role(*, actor, association, access, role):
    from apps.associations.permissions import ensure_permission

    ensure_permission(actor, association, "roles.manage")
    _ensure_assignable(role)
    locked = _lock_access(access, association)
    if role == AssociationRole.Role.ADMIN and not _is_admin(actor, association):
        raise PermissionDenied(_("Solo una cuenta con rol de administración puede conceder ese rol."))
    if not locked.is_active:
        raise ValidationError(_("El acceso está desactivado. Reactívalo antes de concederle roles."))
    _assignment, created = AssociationRole.objects.get_or_create(access=locked, role=role)
    if created:
        _record(locked, actor, "role_granted", role)
    return created


@transaction.atomic
def revoke_role(*, actor, association, access, role):
    from apps.associations.permissions import ensure_permission

    ensure_permission(actor, association, "roles.manage")
    _ensure_assignable(role)
    locked = _lock_access(access, association)
    if role == AssociationRole.Role.ADMIN:
        if not _is_admin(actor, association):
            raise PermissionDenied(_("Solo una cuenta con rol de administración puede quitar ese rol."))
        active_admins = _lock_active_admins(association)
        if locked.pk in active_admins and len(active_admins) <= 1:
            raise ValidationError(
                _("La asociación se quedaría sin ninguna cuenta de administración activa.")
            )
    deleted, _details = AssociationRole.objects.filter(access=locked, role=role).delete()
    if deleted:
        _record(locked, actor, "role_revoked", role)
    return bool(deleted)


@transaction.atomic
def set_access_active(*, actor, association, access, active):
    """Activa o desactiva el acceso de una cuenta a esta asociación.

    La cuenta global y sus accesos a otras asociaciones no cambian.
    """
    ensure_access_manager(actor, association)
    locked = _lock_access(access, association)
    if locked.is_active == active:
        return locked
    holds_admin = locked.role_assignments.filter(role=AssociationRole.Role.ADMIN).exists()
    if holds_admin and not _is_admin(actor, association):
        raise PermissionDenied(
            _("Solo una cuenta con rol de administración puede cambiar el acceso de otra que lo tenga.")
        )
    if not active:
        if locked.account_id == actor.pk:
            raise ValidationError(_("No puedes desactivar tu propio acceso."))
        if holds_admin:
            active_admins = _lock_active_admins(association)
            if locked.pk in active_admins and len(active_admins) <= 1:
                raise ValidationError(
                    _("La asociación se quedaría sin ninguna cuenta de administración activa.")
                )
    locked.is_active = active
    locked.save(update_fields=["is_active"])
    _record(locked, actor, "access_reactivated" if active else "access_deactivated")
    return locked
