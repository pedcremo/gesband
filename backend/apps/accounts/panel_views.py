"""Panel de accesos y roles de una asociación (decisión 0009).

Solo `admin` y `board`. Las reglas (quién concede `admin`, último `admin`,
roles reservados a la plataforma) viven en `apps/accounts/services.py`; aquí
se recogen las acciones, se pide confirmación para las que quitan acceso y se
cuenta el resultado.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.associations.models import AssociationAccess, AssociationRole
from apps.associations.permissions import ACCESS_MANAGER_ROLES, PANEL_ASSIGNABLE_ROLES
from apps.members.models import Member
from config.panel import _association_for

from . import services
from .forms import RoleForm
from .models import AccessChange


def _page_url(association):
    return f"{reverse('panel-access-roles')}?association_id={association.id}"


def _role_label(role):
    return AssociationRole.Role(role).label if role in AssociationRole.Role.values else role


@login_required
@require_http_methods(["GET", "POST"])
def access_roles(request):
    association = _association_for(request, ACCESS_MANAGER_ROLES)
    if request.method == "POST":
        return _handle_action(request, association)
    accesses = (
        AssociationAccess.objects.filter(association=association)
        .select_related("account")
        .prefetch_related(
            "role_assignments",
            Prefetch(
                "account__member_profiles",
                queryset=Member.objects.filter(association=association),
                to_attr="local_profiles",
            ),
        )
        .order_by("-is_active", "account__last_name", "account__first_name", "account__email")
    )
    rows = []
    for access in accesses:
        roles = sorted(access.role_assignments.all(), key=lambda item: item.get_role_display())
        rows.append(
            {
                "access": access,
                "member": access.account.local_profiles[0] if access.account.local_profiles else None,
                "roles": [
                    {"code": item.role, "label": item.get_role_display(), "removable": item.role in PANEL_ASSIGNABLE_ROLES}
                    for item in roles
                ],
                "is_self": access.account_id == request.user.pk,
            }
        )
    changes = AccessChange.objects.filter(association=association).select_related("access__account", "actor")[:20]
    return render(
        request,
        "accounts/access_roles.html",
        {
            "association": association,
            "rows": rows,
            "role_form": RoleForm(),
            "changes": [
                {"change": change, "role_label": _role_label(change.role) if change.role else ""} for change in changes
            ],
        },
    )


def _handle_action(request, association):
    access_id = request.POST.get("access_id", "")
    if not access_id.isdigit():
        raise Http404(_("Ese acceso no pertenece a esta asociación."))
    access = get_object_or_404(AssociationAccess.objects.select_related("account"), pk=access_id, association=association)
    action = request.POST.get("action")
    confirmed = request.POST.get("confirmed") == "1"
    try:
        if action == "grant_role":
            form = RoleForm(request.POST)
            if not form.is_valid():
                raise ValidationError(_("Elige un rol válido."))
            role = form.cleaned_data["role"]
            if services.grant_role(actor=request.user, association=association, access=access, role=role):
                messages.success(request, _("Rol «%(role)s» concedido a %(account)s.") % {"role": _role_label(role), "account": access.account})
            else:
                messages.info(request, _("%(account)s ya tenía ese rol.") % {"account": access.account})
        elif action == "revoke_role":
            role = request.POST.get("role", "")
            if not confirmed:
                return _confirm(
                    request,
                    association,
                    access,
                    title=_("Quitar el rol «%(role)s» a %(account)s") % {"role": _role_label(role), "account": access.account},
                    explanation=_("Perderá los permisos de ese rol en esta asociación. Podrás concedérselo de nuevo."),
                    fields={"action": action, "role": role},
                    confirm_label=_("Quitar rol"),
                )
            services.revoke_role(actor=request.user, association=association, access=access, role=role)
            messages.success(request, _("Rol «%(role)s» retirado a %(account)s.") % {"role": _role_label(role), "account": access.account})
        elif action == "deactivate":
            if not confirmed:
                return _confirm(
                    request,
                    association,
                    access,
                    title=_("Desactivar el acceso de %(account)s") % {"account": access.account},
                    explanation=_(
                        "No podrá entrar en esta asociación ni en la app ni en el panel. Su cuenta, sus roles y su "
                        "acceso a otras asociaciones se conservan, y podrás reactivarlo."
                    ),
                    fields={"action": action},
                    confirm_label=_("Desactivar acceso"),
                )
            services.set_access_active(actor=request.user, association=association, access=access, active=False)
            messages.success(request, _("Acceso de %(account)s desactivado.") % {"account": access.account})
        elif action == "reactivate":
            services.set_access_active(actor=request.user, association=association, access=access, active=True)
            messages.success(request, _("Acceso de %(account)s reactivado.") % {"account": access.account})
        else:
            messages.error(request, _("Acción no reconocida."))
    except PermissionDenied as error:
        messages.error(request, str(error) or _("No tienes permisos para realizar esta acción."))
    except ValidationError as error:
        for text in error.messages:
            messages.error(request, text)
    return redirect(_page_url(association))


def _confirm(request, association, access, *, title, explanation, fields, confirm_label):
    return render(
        request,
        "members/confirm.html",
        {
            "association": association,
            "title": title,
            "explanation": explanation,
            "action_url": reverse("panel-access-roles"),
            "fields": {"access_id": access.pk, **fields},
            "confirm_label": confirm_label,
            "cancel_url": _page_url(association),
        },
    )
