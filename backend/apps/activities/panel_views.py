"""Página «Pagos a músicos» del panel de la junta (decisión 0011)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from config.panel import _association_for

from .models import ActivityPayment, Invitation
from .payments import (
    PAYMENT_MANAGER_ROLES,
    ZERO,
    association_earnings,
    ensure_payment_manager,
    mark_all_present_paid,
    mark_paid,
    void_payment,
)


def _get_or_404(queryset, raw_id):
    """Objeto del queryset (ya filtrado por asociación) o 404, también con ids mal formados."""
    try:
        return queryset.get(pk=raw_id)
    except (queryset.model.DoesNotExist, ValueError, ValidationError) as exc:
        raise Http404 from exc


def _report_mark_paid(request, invitation, association):
    try:
        _payment, created = mark_paid(invitation, request.user, association)
    except ValidationError as exc:
        for error in exc.messages:
            messages.error(request, error)
        return
    if created:
        messages.success(request, _("Pago registrado."))
    else:
        messages.info(request, _("Ese pago ya estaba registrado."))


def handle_activity_payment_action(request, association, activity):
    """Acciones de pago del detalle de una actividad.

    El detalle lo abren todos los gestores, pero pagar es de `admin` y `board`:
    se comprueba antes de leer nada del formulario.
    """
    ensure_payment_manager(request.user, association)
    action = request.POST.get("payment_action")
    if action == "mark_paid":
        invitation = _get_or_404(Invitation.objects.filter(activity=activity), request.POST.get("invitation_id"))
        _report_mark_paid(request, invitation, association)
    elif action == "mark_all_paid":
        created = mark_all_present_paid(activity, request.user, association)
        if created:
            messages.success(request, _("Se han registrado %(count)s pagos.") % {"count": created})
        else:
            messages.info(request, _("No quedaba ningún presente pendiente de pago."))
    elif action == "void_payment":
        payment = _get_or_404(
            ActivityPayment.objects.filter(invitation__activity=activity), request.POST.get("payment_id")
        )
        _payment, voided = void_payment(payment, request.user, association)
        if voided:
            messages.success(request, _("Pago anulado. Queda en el historial."))
        else:
            messages.info(request, _("Ese pago ya estaba anulado."))
    detail_url = reverse("panel-activity-detail", kwargs={"activity_id": activity.id})
    return redirect(f"{detail_url}?association_id={association.id}#pagos")


@login_required
@require_http_methods(["GET", "POST"])
def payments_overview(request):
    """Adeudado por músico, con su desglose; solo `admin` y `board`.

    Desde el desglose se puede marcar como pagada una convocatoria concreta.
    """
    association = _association_for(request, PAYMENT_MANAGER_ROLES)
    if request.method == "POST":
        invitation = _get_or_404(
            Invitation.objects.filter(activity__association=association), request.POST.get("invitation_id")
        )
        _report_mark_paid(request, invitation, association)
        return redirect(f"{reverse('panel-payments')}?association_id={association.id}")

    rows = association_earnings(association)
    return render(
        request,
        "activities/payments.html",
        {
            "association": association,
            "rows": rows,
            "owed_total": sum((summary.owed_total for _member, summary in rows), ZERO),
            "paid_total": sum((summary.paid_total for _member, summary in rows), ZERO),
            "incidents": sum(summary.incidents for _member, summary in rows),
        },
    )
