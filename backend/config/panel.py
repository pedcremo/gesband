from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.activities.forms import ActivityChangeForm
from apps.activities.models import Activity
from apps.activities.services import (
    announce_activity_change,
    cancel_activity,
    changed_activity_fields,
    publish_activity,
)
from apps.accounts.models import AccessInvitation
from apps.accounts.services import deliver_access_invitation, issue_access_invitation, revoke_access_invitation
from apps.associations.models import AssociationAccess, AssociationRole
from apps.associations.permissions import MANAGER_ROLES
from apps.members.models import ImportBatch, Member
from apps.members.services import confirm_import, inspect_import, parse_import, suggest_import_mapping


IMPORT_FIELDS = [
    ("external_id", gettext_lazy("Identificador externo")),
    ("first_name", gettext_lazy("Nombre")),
    ("last_name", gettext_lazy("Apellidos (juntos)")),
    ("first_surname", gettext_lazy("Primer apellido")),
    ("second_surname", gettext_lazy("Segundo apellido")),
    ("national_id", gettext_lazy("DNI/NIE")),
    ("address", gettext_lazy("Dirección")),
    ("phone", gettext_lazy("Teléfono")),
    ("email", gettext_lazy("Correo electrónico")),
    ("kind", gettext_lazy("Tipo de miembro")),
]


def _access_for(request, roles=MANAGER_ROLES):
    """Acceso de la cuenta a la asociación pedida con alguno de esos roles.

    Falta de rol y falta de acceso responden igual, un 403: quien no puede entrar
    tampoco tiene por qué averiguar si la asociación existe.
    """
    association_id = request.GET.get("association_id") or request.POST.get("association_id")
    access = (
        AssociationAccess.objects.filter(
            account=request.user,
            is_active=True,
            association__is_active=True,
            role_assignments__role__in=roles,
        )
        .distinct()
        .select_related("association")
    )
    try:
        selected = access.filter(association_id=association_id).first() if association_id else access.first()
    except (ValueError, DjangoValidationError):
        selected = None
    if not selected:
        raise PermissionDenied(_("No tienes permisos para acceder a esta parte del panel de la junta."))
    return selected


def _association_for(request, roles=MANAGER_ROLES):
    return _access_for(request, roles).association


def _roles_in(request, association):
    """Roles de la cuenta en esa asociación, para decidir qué ofrecer."""
    return set(
        AssociationRole.objects.filter(
            access__account=request.user,
            access__association=association,
            access__is_active=True,
        ).values_list("role", flat=True)
    )


@login_required
def dashboard(request):
    association = _association_for(request)
    activities = Activity.objects.filter(association=association).annotate(invited=Count("invitations"))[:10]
    context = {
        "association": association,
        "members_count": Member.objects.filter(association=association, status=Member.Status.ACTIVE).count(),
        "activities": activities,
        "now": timezone.now(),
    }
    return render(request, "shared/dashboard.html", context)


@login_required
def members(request):
    association = _association_for(request)
    member_list = Member.objects.filter(association=association).prefetch_related("member_instruments__instrument")
    return render(
        request,
        "members/list.html",
        {
            "association": association,
            "members": member_list,
            "can_manage_census": AssociationRole.Role.ADMIN in _roles_in(request, association),
        },
    )


@login_required
def member_access_invitations(request):
    association = _association_for(request, {AssociationRole.Role.ADMIN})
    member_list = Member.objects.filter(
        association=association,
        status=Member.Status.ACTIVE,
        kind=Member.Kind.MUSICIAN,
    ).select_related("account")
    if request.method == "POST" and request.POST.get("revoke_id"):
        invitation = get_object_or_404(
            AccessInvitation,
            id=request.POST["revoke_id"],
            association=association,
        )
        try:
            revoke_access_invitation(invitation=invitation, revoked_by=request.user)
        except DjangoValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
        else:
            messages.success(request, _("Invitación revocada."))
        return redirect(f"{reverse('member-access-invitations')}?association_id={association.id}")

    if request.method == "POST" and request.POST.get("action") in {"invite_selected", "invite_all"}:
        candidates = member_list.filter(account__isnull=True).exclude(email="")
        if request.POST["action"] == "invite_selected":
            candidates = candidates.filter(id__in=request.POST.getlist("member_ids"))
        sent = 0
        failed = 0
        skipped = 0
        for member in candidates:
            try:
                invitation, token = issue_access_invitation(member=member, created_by=request.user)
            except DjangoValidationError:
                skipped += 1
                continue
            activation_url = request.build_absolute_uri(
                reverse("account-invitation-activate", kwargs={"token": token})
            )
            if deliver_access_invitation(
                invitation=invitation,
                token=token,
                activation_url=activation_url,
            ):
                sent += 1
            else:
                failed += 1
        if sent:
            messages.success(request, _("Se han enviado %(count)s invitaciones.") % {"count": sent})
        if failed:
            messages.error(
                request,
                _("%(count)s invitaciones no pudieron enviarse; puedes reenviarlas.") % {"count": failed},
            )
        if skipped or not (sent or failed):
            messages.info(
                request,
                _("No se enviaron %(count)s selecciones porque ya tienen cuenta o no son elegibles.")
                % {"count": skipped or len(request.POST.getlist("member_ids"))},
            )
        return redirect(f"{reverse('member-access-invitations')}?association_id={association.id}")

    latest_by_member = {}
    for invitation in AccessInvitation.objects.filter(association=association).select_related("member"):
        latest_by_member.setdefault(invitation.member_id, invitation)
    rows = [
        {"member": member, "invitation": latest_by_member.get(member.id)}
        for member in member_list
    ]
    return render(
        request,
        "members/access_invitations.html",
        {"association": association, "rows": rows, "now": timezone.now()},
    )


@login_required
def member_import_start(request):
    association = _association_for(request, {AssociationRole.Role.ADMIN})
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, _("Adjunta un CSV o XLSX."))
        else:
            try:
                content, content_hash, headers, _rows = inspect_import(upload)
            except DjangoValidationError as exc:
                for error in exc.messages:
                    messages.error(request, error)
            else:
                existing = ImportBatch.objects.filter(
                    association=association,
                    content_hash=content_hash,
                ).first()
                if existing:
                    messages.info(request, _("Este fichero ya se había cargado; se muestra el lote existente."))
                    detail_url = reverse("member-import-detail", kwargs={"batch_id": existing.id})
                    return redirect(f"{detail_url}?association_id={association.id}")
                batch = ImportBatch(
                    association=association,
                    created_by=request.user,
                    filename=upload.name[:255],
                    content_hash=content_hash,
                    source_headers=headers,
                    mapping=suggest_import_mapping(headers),
                )
                batch.source_file.save(upload.name, ContentFile(content), save=False)
                batch.save()
                detail_url = reverse("member-import-detail", kwargs={"batch_id": batch.id})
                return redirect(f"{detail_url}?association_id={association.id}")
    batches = ImportBatch.objects.filter(association=association)[:20]
    return render(
        request,
        "members/import_start.html",
        {"association": association, "batches": batches},
    )


@login_required
def member_import_detail(request, batch_id):
    association = _association_for(request, {AssociationRole.Role.ADMIN})
    batch = get_object_or_404(ImportBatch, id=batch_id, association=association)
    displayed_mapping = batch.mapping
    if request.method == "POST" and request.POST.get("action") == "preview":
        mapping = {
            header: target
            for index, header in enumerate(batch.source_headers)
            if (target := request.POST.get(f"column_{index}", ""))
        }
        displayed_mapping = mapping
        if not batch.source_file:
            messages.error(request, _("El fichero temporal ya no está disponible."))
        else:
            try:
                with batch.source_file.open("rb") as upload:
                    _content, content_hash, preview = parse_import(upload, mapping)
                if content_hash != batch.content_hash:
                    raise DjangoValidationError(_("El fichero temporal no coincide con la carga original."))
            except DjangoValidationError as exc:
                for error in exc.messages:
                    messages.error(request, error)
            else:
                batch.mapping = mapping
                batch.preview = preview
                batch.status = ImportBatch.Status.PREVIEW
                batch.save(update_fields=["mapping", "preview", "status"])
                messages.success(request, _("Previsualización generada; el censo todavía no se ha modificado."))
                detail_url = reverse("member-import-detail", kwargs={"batch_id": batch.id})
                return redirect(f"{detail_url}?association_id={association.id}")
    elif request.method == "POST" and request.POST.get("action") == "confirm":
        try:
            result = confirm_import(batch)
        except DjangoValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
        else:
            messages.success(
                request,
                _("Importación confirmada: %(created)s altas, %(updated)s actualizaciones y %(rejected)s rechazos.")
                % result,
            )
            detail_url = reverse("member-import-detail", kwargs={"batch_id": batch.id})
            return redirect(f"{detail_url}?association_id={association.id}")
    batch.refresh_from_db()
    mapping_rows = [
        {"header": header, "selected": displayed_mapping.get(header, "")}
        for header in batch.source_headers
    ]
    return render(
        request,
        "members/import_detail.html",
        {
            "association": association,
            "batch": batch,
            "import_fields": IMPORT_FIELDS,
            "mapping_rows": mapping_rows,
            "can_confirm": any(not item["errors"] for item in batch.preview),
        },
    )


@login_required
def member_import_template(request):
    association = _association_for(request, {AssociationRole.Role.ADMIN})
    content = (
        "external_id,first_name,first_surname,second_surname,national_id,address,phone,email,kind\r\n"
        "MUS-001,Marina,Soler,Ferri,,Carrer Exemple 1,+34960000001,marina@example.invalid,musician\r\n"
    )
    response = HttpResponse("\ufeff" + content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="plantilla-miembros.csv"'
    return response


@login_required
def activity_detail(request, activity_id):
    association = _association_for(request)
    activity = get_object_or_404(Activity.objects.prefetch_related("invitations__member", "invitations__attendance"), id=activity_id, association=association)
    change_form = ActivityChangeForm(instance=activity)
    if request.method == "POST":
        if "publish" in request.POST:
            result = publish_activity(activity, request.user)
            activity = result["activity"]
            messages.success(
                request,
                _("Actividad publicada. Se ha avisado a %(notified)s personas convocadas.") % result,
            )
        elif "cancel" in request.POST:
            try:
                result = cancel_activity(activity, request.user, reason=request.POST.get("reason", ""))
            except DRFValidationError as error:
                messages.error(request, " ".join(error.detail))
                return redirect("activity-detail", activity_id=activity.id)
            activity = result["activity"]
            messages.success(
                request,
                _("Actividad cancelada. Se ha avisado a %(notified)s personas convocadas.") % result,
            )
        elif "save_changes" in request.POST:
            # El formulario escribe sobre `activity` al validar, asi que la
            # comparacion necesita una copia anterior recien leida.
            before = Activity.objects.get(pk=activity.pk)
            change_form = ActivityChangeForm(request.POST, instance=activity)
            if not change_form.is_valid():
                return _render_activity_detail(request, association, activity, change_form)
            changed = changed_activity_fields(before, change_form.cleaned_data)
            activity = change_form.save()
            notice = announce_activity_change(activity, changed, request.user)
            _report_change_notice(request, notice)
            change_form = ActivityChangeForm(instance=activity)
        elif "invite_all_musicians" in request.POST:
            from apps.activities.services import invite_members, notify_activity

            result = invite_members(
                activity,
                Member.objects.filter(association=association),
                mandatory=request.POST.get("is_mandatory") == "1",
            )
            activity = result["activity"]
            if activity.status == Activity.Status.PUBLISHED:
                notify_activity(activity, _("Nueva convocatoria"), activity.title)
            messages.success(
                request,
                _(
                    "Convocatoria preparada para %(eligible)s músicos activos: "
                    "%(created)s nuevas y %(existing)s ya existentes."
                )
                % result,
            )
        elif request.POST.get("attendance_id"):
            invitation = activity.invitations.get(id=request.POST["attendance_id"])
            from apps.activities.services import record_attendance

            record_attendance(invitation, request.user, request.POST.get("attendance", "present"))
            messages.success(request, _("Asistencia actualizada."))
        return redirect("activity-detail", activity_id=activity.id)
    return _render_activity_detail(request, association, activity, change_form)


def _render_activity_detail(request, association, activity, change_form):
    active_musicians_count = Member.objects.filter(
        association=association,
        status=Member.Status.ACTIVE,
        kind=Member.Kind.MUSICIAN,
    ).count()
    return render(
        request,
        "activities/detail.html",
        {
            "association": association,
            "activity": activity,
            "active_musicians_count": active_musicians_count,
            "change_form": change_form,
        },
    )


def _report_change_notice(request, notice):
    """Cuenta a la junta que ha pasado con el cambio que acaba de guardar."""
    if not notice["fields"]:
        messages.success(request, _("Actividad actualizada. No había nada que avisar."))
        return
    if notice["reset"]:
        messages.success(
            request,
            _(
                "Actividad actualizada. Se ha avisado a %(notified)s personas y se han "
                "anulado %(reset)s respuestas: el cambio de fecha o lugar obliga a "
                "confirmar de nuevo."
            )
            % notice,
        )
    else:
        messages.success(
            request,
            _("Actividad actualizada. Se ha avisado a %(notified)s personas convocadas.") % notice,
        )
    if notice["deadline_passed"]:
        messages.warning(
            request,
            _(
                "El plazo de respuesta ya ha terminado, así que nadie puede volver a "
                "confirmar. Amplíalo para recoger las respuestas."
            ),
        )
