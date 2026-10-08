"""Imagen de la banda en el panel (decisión 0010). Solo `admin` y `board`."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from config.panel import _association_for

from . import services
from .forms import BrandingForm
from .models import Association
from .permissions import ACCESS_MANAGER_ROLES


@login_required
@require_http_methods(["GET", "POST"])
def branding(request):
    association = _association_for(request, ACCESS_MANAGER_ROLES)
    # El formulario trabaja sobre una copia: si no valida, la cabecera sigue con la marca guardada.
    draft = Association.objects.get(pk=association.pk)
    if request.method == "POST":
        form = BrandingForm(request.POST, request.FILES, instance=draft)
        if form.is_valid():
            try:
                services.update_branding(
                    actor=request.user,
                    association=association,
                    data={field: form.cleaned_data[field] for field in services.BRANDING_FIELDS},
                    logo=form.cleaned_data.get("logo"),
                    remove_logo=form.cleaned_data.get("remove_logo"),
                )
            except ValidationError as exc:
                for field, errors in getattr(exc, "message_dict", {"logo": exc.messages}).items():
                    form.add_error(field if field in form.fields else None, errors)
            else:
                messages.success(request, _("Imagen de la banda guardada."))
                return redirect(f"{reverse('panel-branding')}?association_id={association.id}")
    else:
        form = BrandingForm(instance=draft)
    return render(request, "associations/branding.html", {"association": association, "form": form})
