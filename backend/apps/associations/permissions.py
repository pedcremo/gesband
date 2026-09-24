from rest_framework.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from .models import AssociationAccess, AssociationRole

MANAGER_ROLES = {
    AssociationRole.Role.ADMIN,
    AssociationRole.Role.BOARD,
    AssociationRole.Role.ORGANIZER,
    AssociationRole.Role.DIRECTOR,
}

# Roles que participan en la vida de la banda y por tanto leen sus datos.
# `platform` y `web_editor` quedan fuera a proposito: operan la plataforma o el
# complemento web, no asisten a ensayos ni salidas.
PARTICIPANT_ROLES = {AssociationRole.Role.MEMBER, *MANAGER_ROLES}


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


# Permisos que son de la cuenta, no de la asociacion; `activities.view`, en
# cambio, depende de participar en la banda.
ACCOUNT_PERMISSIONS = {"association.view", "notifications.view", "devices.manage_own"}
PARTICIPANT_PERMISSIONS = {"activities.view", "polls.view"}
MANAGER_PERMISSIONS = {
    "members.view",
    "members.manage",
    "activities.manage",
    "attendance.manage",
    "transport.manage",
    "polls.manage",
}
ADMIN_PERMISSIONS = {"association.manage", "imports.manage"}


def permissions_for_roles(roles):
    """Permisos que conceden esos roles, tal como los aplica el servidor."""
    roles = set(roles)
    permissions = set(ACCOUNT_PERMISSIONS)
    if roles.intersection(PARTICIPANT_ROLES):
        permissions |= PARTICIPANT_PERMISSIONS
    if roles.intersection(MANAGER_ROLES):
        permissions |= MANAGER_PERMISSIONS
    if AssociationRole.Role.ADMIN in roles:
        permissions |= ADMIN_PERMISSIONS
    return permissions


def permissions_for(account, association):
    """Permisos de la cuenta en la asociacion, ordenados; `["*"]` para superusuarios.

    Es la unica fuente de lo que se anuncia en /api/v1/auth/me y en la pagina
    «Mi acceso» del panel: si cambia un permiso, cambia aqui.
    """
    if account.is_superuser:
        return ["*"]
    access = AssociationAccess.objects.filter(account=account, association=association, is_active=True).first()
    if not access:
        return []
    return sorted(permissions_for_roles(access.role_assignments.values_list("role", flat=True)))


# Capacidades que se explican a la persona en «Mi acceso», en el orden en que se
# muestran. Cada una se concede si tiene el permiso indicado.
CAPABILITIES = [
    ("members.view", gettext_lazy("Ver el censo")),
    ("members.manage", gettext_lazy("Gestionar el censo")),
    ("imports.manage", gettext_lazy("Importar miembros desde CSV o XLSX")),
    ("activities.view", gettext_lazy("Ver actividades y responder a las convocatorias")),
    ("activities.manage", gettext_lazy("Crear y publicar actividades")),
    ("activities.manage", gettext_lazy("Convocar músicos")),
    ("attendance.manage", gettext_lazy("Pasar lista")),
    ("transport.manage", gettext_lazy("Organizar el transporte")),
    ("polls.view", gettext_lazy("Ver y votar encuestas")),
    ("polls.manage", gettext_lazy("Crear, abrir y publicar encuestas")),
    ("association.manage", gettext_lazy("Configurar la asociación")),
]


def capabilities_for(permissions):
    """Tabla «puedes / no puedes» a partir de la salida de `permissions_for`."""
    granted = set(permissions)
    everything = "*" in granted
    return [
        {"permission": code, "label": label, "allowed": everything or code in granted}
        for code, label in CAPABILITIES
    ]
