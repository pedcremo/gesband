"""Panel de la junta para mantener las fichas del censo (decisión 0009).

Las vistas traducen formularios a llamadas de `services` y cuentan el
resultado. Pueden usarlas `admin`, `board`, `organizer` y `director`; el
borrado físico, solo `admin`. Una ficha de otra asociación responde 404.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from apps.associations.models import AssociationRole
from apps.associations.permissions import has_permission
from config.panel import _association_for

from . import services
from .forms import MemberForm, PhotoForm
from .models import Member, MemberInstrument


def _detail_url(member):
    url = reverse("panel-member-detail", kwargs={"member_id": member.pk})
    return f"{url}?association_id={member.association_id}"


def _list_url(association):
    return f"{reverse('panel-members')}?association_id={association.id}"


def _member_in(association, member_id):
    return get_object_or_404(
        Member.objects.select_related("association").prefetch_related(
            Prefetch("member_instruments", queryset=MemberInstrument.objects.select_related("instrument__section")),
            "positions",
        ),
        pk=member_id,
        association=association,
    )


def _apply_errors(form, error):
    """Coloca los errores del servicio junto a su campo, o arriba del formulario."""
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            target = field if field in form.fields else None
            for item in errors:
                form.add_error(target, item.messages)
    else:
        form.add_error(None, error.messages)


def _save_from_form(form, request, member=None):
    instruments = list(form.cleaned_data["instruments"])
    primary = form.cleaned_data["primary_instrument"]
    positions = form.cleaned_data["positions"]
    if member is None:
        return services.create_member(
            association=form.association,
            actor=request.user,
            data=form.member_data(),
            instruments=instruments,
            primary_instrument=primary,
            positions=positions,
        )
    return services.update_member(
        member=member,
        actor=request.user,
        data=form.member_data(),
        instruments=instruments,
        primary_instrument=primary,
        positions=positions,
    )


@login_required
@require_http_methods(["GET", "POST"])
def member_create(request):
    association = _association_for(request)
    form = MemberForm(request.POST or None, association=association, instance=Member(association=association))
    if request.method == "POST" and form.is_valid():
        try:
            member = _save_from_form(form, request)
        except ValidationError as error:
            _apply_errors(form, error)
        else:
            messages.success(request, _("Ficha creada."))
            return redirect(_detail_url(member))
    return render(
        request,
        "members/form.html",
        {"association": association, "form": form, "member": None},
    )


@login_required
@require_http_methods(["GET", "POST"])
def member_detail(request, member_id):
    association = _association_for(request)
    member = _member_in(association, member_id)
    # El formulario trabaja sobre una copia: si el servicio rechaza el cambio,
    # la página no debe mostrar como guardado lo que no se guardó.
    form = MemberForm(
        request.POST or None,
        association=association,
        instance=Member.objects.get(pk=member.pk),
    )
    if request.method == "POST" and form.is_valid():
        try:
            member = _save_from_form(form, request, member)
        except ValidationError as error:
            _apply_errors(form, error)
        else:
            messages.success(request, _("Ficha actualizada."))
            return redirect(_detail_url(member))
    return _render_detail(request, association, member, form)


def _render_detail(request, association, member, form, photo_form=None, status=200):
    return render(
        request,
        "members/form.html",
        {
            "association": association,
            "form": form,
            "photo_form": photo_form or PhotoForm(),
            "member": member,
            "history": services.member_history(member),
            "can_delete": has_permission(request.user, association, "members.delete"),
            "deletion_blockers": services.member_deletion_blockers(member),
        },
        status=status,
    )


@login_required
@require_http_methods(["GET", "POST"])
def member_photo(request, member_id):
    """La foto privada se sirve tras comprobar permisos, nunca desde /media/."""
    association = _association_for(request)
    member = _member_in(association, member_id)
    if request.method == "GET":
        if not member.photo:
            raise Http404(_("Esta ficha no tiene foto."))
        response = FileResponse(member.photo.open("rb"), content_type="image/webp")
        response["Cache-Control"] = "private, no-store"
        return response
    if request.POST.get("action") == "delete":
        services.delete_member_photo(member=member, actor=request.user)
        messages.success(request, _("Foto eliminada."))
        return redirect(_detail_url(member))
    photo_form = PhotoForm(request.POST, request.FILES)
    if photo_form.is_valid():
        try:
            services.replace_member_photo(member=member, actor=request.user, upload=photo_form.cleaned_data["photo"])
        except ValidationError as error:
            photo_form.add_error("photo", error.messages)
        else:
            messages.success(request, _("Foto guardada."))
            return redirect(_detail_url(member))
    form = MemberForm(association=association, instance=member)
    return _render_detail(request, association, member, form, photo_form=photo_form, status=400)


@login_required
@require_POST
def member_status(request, member_id):
    """Baja (con confirmación) o reactivación de una ficha."""
    association = _association_for(request)
    member = _member_in(association, member_id)
    status = request.POST.get("status")
    if status == Member.Status.INACTIVE and request.POST.get("confirmed") != "1":
        return render(
            request,
            "members/confirm.html",
            {
                "association": association,
                "title": _("Dar de baja a %(member)s") % {"member": member},
                "explanation": _(
                    "La ficha quedará inactiva: no se la podrá convocar ni invitar, pero se conservan "
                    "sus convocatorias, respuestas y asistencia. Podrás reactivarla cuando quieras."
                ),
                "action_url": reverse("panel-member-status", kwargs={"member_id": member.pk}),
                "fields": {"status": Member.Status.INACTIVE},
                "confirm_label": _("Dar de baja"),
                "cancel_url": _detail_url(member),
            },
        )
    try:
        member = services.set_member_status(member=member, actor=request.user, status=status)
    except ValidationError as error:
        for text in error.messages:
            messages.error(request, text)
    else:
        if member.status == Member.Status.ACTIVE:
            messages.success(request, _("Ficha reactivada."))
        else:
            messages.success(request, _("Ficha dada de baja. Su historial se conserva."))
    return redirect(_detail_url(member))


@login_required
@require_http_methods(["GET", "POST"])
def member_delete(request, member_id):
    """Borrado físico: solo `admin`, con confirmación y sin historial."""
    association = _association_for(request, {AssociationRole.Role.ADMIN})
    member = _member_in(association, member_id)
    blockers = services.member_deletion_blockers(member)
    if request.method == "POST" and request.POST.get("confirmed") == "1":
        try:
            services.delete_member(member=member, actor=request.user)
        except ValidationError as error:
            for text in error.messages:
                messages.error(request, text)
            return redirect(_detail_url(member))
        messages.success(request, _("Ficha borrada definitivamente."))
        return redirect(_list_url(association))
    return render(
        request,
        "members/confirm.html",
        {
            "association": association,
            "title": _("Borrar definitivamente a %(member)s") % {"member": member},
            "explanation": _(
                "El borrado no se puede deshacer. Solo se permite si la ficha no tiene historial ni cuenta vinculada."
            ),
            "blockers": blockers,
            "action_url": reverse("panel-member-delete", kwargs={"member_id": member.pk}),
            "fields": {},
            "confirm_label": _("Borrar definitivamente"),
            "cancel_url": _detail_url(member),
        },
        status=409 if blockers and request.method == "POST" else 200,
    )
