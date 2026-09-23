from rest_framework.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from .models import AssociationAccess, AssociationRole

MANAGER_ROLES = {
    AssociationRole.Role.ADMIN,
    AssociationRole.Role.BOARD,
    AssociationRole.Role.ORGANIZER,
    AssociationRole.Role.DIRECTOR,
}


def get_access_or_403(user, association_id):
    if not user.is_authenticated:
        raise PermissionDenied(_("Autenticación requerida."))
    try:
        return AssociationAccess.objects.select_related("association").prefetch_related("role_assignments").get(
            account=user, association_id=association_id, is_active=True, association__is_active=True
        )
    except AssociationAccess.DoesNotExist as exc:
        raise PermissionDenied(_("No tienes acceso a esta asociación.")) from exc


def require_roles(user, association_id, roles):
    access = get_access_or_403(user, association_id)
    if user.is_superuser:
        return access
    assigned = set(access.role_assignments.values_list("role", flat=True))
    if not assigned.intersection(set(roles)):
        raise PermissionDenied(_("No tienes permisos para realizar esta acción."))
    return access


def accessible_association_ids(user):
    if user.is_superuser:
        from .models import Association

        return Association.objects.filter(is_active=True).values_list("id", flat=True)
    return AssociationAccess.objects.filter(account=user, is_active=True, association__is_active=True).values_list(
        "association_id", flat=True
    )
