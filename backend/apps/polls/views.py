"""Panel de la junta para las encuestas (ANALISIS.md 3.7).

Las vistas solo traducen formularios a llamadas de `services` y cuentan el
resultado. El anonimato también se respeta aquí: mientras se vota, el panel
muestra el total de participación pero nunca quién ha votado, porque cruzarlo
con el recuento provisional delataría el voto de cada cual.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.associations.models import AssociationAccess
from apps.associations.permissions import MANAGER_ROLES
from config.panel import _association_for

from . import services
from .forms import PollForm, RecipientSelectionForm
from .models import Poll


def _error_messages(error):
    """Textos planos de una `ValidationError` de DRF, sea lista, dict o texto."""
    detail = error.detail
    if isinstance(detail, dict):
        return {field: _flatten(value) for field, value in detail.items()}
    return {None: _flatten(detail)}


def _flatten(value):
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _flatten(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _flatten(item)]
    return [str(value)]


def _report_errors(request, error):
    for texts in _error_messages(error).values():
        for text in texts:
            messages.error(request, text)


def _form_errors(form, error):
    """Coloca cada error del servicio junto a su campo si el formulario lo tiene."""
    for field, texts in _error_messages(error).items():
        form.add_error(field if field in form.fields else None, texts)


def _detail_url(poll):
    url = reverse("panel-poll-detail", kwargs={"poll_id": poll.pk})
    return f"{url}?association_id={poll.association_id}"


def _managed_poll(request, poll_id):
    """Encuesta de una asociación que la cuenta gestiona.

    Sin rol de junta en ninguna asociación, 403 como el resto del panel. Con
    rol, una encuesta ajena responde igual que una inexistente: 404.
    """
    managed = AssociationAccess.objects.filter(
        account=request.user,
        is_active=True,
        association__is_active=True,
        role_assignments__role__in=MANAGER_ROLES,
    ).values_list("association_id", flat=True)
    if not managed.exists():
        raise PermissionDenied(_("No tienes permisos para acceder a esta parte del panel de la junta."))
    return get_object_or_404(
        Poll.objects.select_related("association").prefetch_related("options"),
        pk=poll_id,
        association_id__in=managed,
    )


def _state(poll):
    if poll.status == Poll.Status.OPEN:
        return "awaiting" if poll.is_awaiting_publication else "open"
    return poll.status


@login_required
def poll_list(request):
    association = _association_for(request)
    polls = Poll.objects.filter(association=association).annotate(
        recipients_count=Count("recipients", distinct=True),
        voted_count=Count("recipients", filter=Q(recipients__has_voted=True), distinct=True),
    )
    rows = [{"poll": poll, "state": _state(poll)} for poll in polls]
    return render(request, "polls/list.html", {"association": association, "rows": rows})


@login_required
def poll_create(request):
    association = _association_for(request)
    form = PollForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            poll = services.create_poll(
                association=association,
                account=request.user,
                question=form.cleaned_data["question"],
                description=form.cleaned_data["description"],
                closes_at=form.cleaned_data["closes_at"],
                options=form.option_labels(),
            )
        except DRFValidationError as error:
            _form_errors(form, error)
        else:
            messages.success(request, _("Encuesta guardada en borrador. Elige ahora a quién se consulta."))
            return redirect(_detail_url(poll))
    return render(request, "polls/new.html", {"association": association, "form": form})


@login_required
def poll_detail(request, poll_id):
    poll = _managed_poll(request, poll_id)
    association = poll.association
    poll_form = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_draft":
            poll_form = PollForm.for_poll(poll, request.POST)
            if poll_form.is_valid():
                try:
                    services.update_draft(
                        poll,
                        question=poll_form.cleaned_data["question"],
                        description=poll_form.cleaned_data["description"],
                        closes_at=poll_form.cleaned_data["closes_at"],
                        options=poll_form.option_labels(),
                    )
                except DRFValidationError as error:
                    if poll.status != Poll.Status.DRAFT:
                        # Ya no hay formulario que mostrar: se cuenta arriba.
                        _report_errors(request, error)
                        return redirect(_detail_url(poll))
                    _form_errors(poll_form, error)
                else:
                    messages.success(request, _("Borrador actualizado."))
                    return redirect(_detail_url(poll))
            poll.refresh_from_db()
        else:
            _handle_action(request, poll, action)
            if action == "delete_draft" and not Poll.objects.filter(pk=poll.pk).exists():
                return redirect(f"{reverse('panel-polls')}?association_id={association.id}")
            return redirect(_detail_url(poll))
    return _render_detail(request, poll, poll_form)


def _handle_action(request, poll, action):
    try:
        if action == "set_recipients":
            form = RecipientSelectionForm(poll.association, request.POST)
            form.is_valid()  # Las casillas no válidas se descartan, nunca invalidan.
            selection = form.cleaned_data
            members = services.eligible_members(
                poll.association,
                member_ids=selection.get("member_ids", []),
                instrument_ids=selection.get("instrument_ids", []),
                section_ids=selection.get("section_ids", []),
                all_active_musicians=selection.get("all_active_musicians", False),
            )
            count = services.set_recipients(poll, members)
            if count:
                messages.success(request, _("Destinatarios guardados: %(count)s personas.") % {"count": count})
            else:
                messages.warning(request, _("No hay destinatarios: la selección no incluye ningún miembro activo."))
        elif action == "open":
            result = services.open_poll(poll, request.user)
            messages.success(
                request,
                _("Votación abierta. Se ha avisado a %(notified)s personas consultadas.") % result,
            )
        elif action == "publish":
            result = services.publish_results(poll, request.user)
            messages.success(
                request,
                _("Resultado publicado. Se ha avisado a %(notified)s personas consultadas.") % result,
            )
        elif action == "cancel":
            result = services.cancel_poll(poll, request.user, request.POST.get("reason", ""))
            messages.success(
                request,
                _("Encuesta anulada. Se ha avisado a %(notified)s personas consultadas.") % result,
            )
        elif action == "delete_draft":
            services.delete_draft(poll)
            messages.success(request, _("Borrador borrado."))
        else:
            messages.error(request, _("Acción no reconocida."))
    except DRFValidationError as error:
        _report_errors(request, error)


def _render_detail(request, poll, poll_form=None):
    state = _state(poll)
    summary = services.tally(poll)
    visibility = services.result_visibility(poll, is_manager=True)
    results = None
    if visibility:
        cast = summary["votes_cast"]
        results = {
            "kind": visibility,
            "votes_cast": cast,
            "options": [
                {**row, "percent": round(row["votes"] * 100 / cast) if cast else 0}
                for row in summary["options"]
            ],
        }
    context = {
        "association": poll.association,
        "poll": poll,
        "state": state,
        "results": results,
        "participation": {"recipients": summary["recipients"], "voted": summary["voted"]},
    }
    if state == "draft":
        recipients = poll.recipients.select_related("member").order_by("member__last_name", "member__first_name")
        context["poll_form"] = poll_form or PollForm.for_poll(poll)
        context["recipient_form"] = RecipientSelectionForm(
            poll.association,
            initial={"member_ids": [str(recipient.member_id) for recipient in recipients]},
        )
        context["draft_recipients"] = [recipient.member for recipient in recipients]
    elif state in {"awaiting", "published"}:
        # Solo con la votación cerrada: mientras se vota, esta lista junto al
        # recuento provisional permitiría deducir el voto de cada persona.
        context["roll"] = poll.recipients.select_related("member").order_by(
            "member__last_name", "member__first_name"
        )
    return render(request, "polls/detail.html", context)
