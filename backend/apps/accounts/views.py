from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .services import activate_access_invitation, invitation_for_token, invitation_is_usable


@require_http_methods(["GET", "POST"])
def activate_invitation(request, token):
    invitation = invitation_for_token(token)
    if not invitation_is_usable(invitation):
        return render(request, "accounts/invitation_invalid.html", status=400)

    errors = []
    if request.method == "POST":
        password = request.POST.get("password", "")
        confirmation = request.POST.get("password_confirmation", "")
        if password != confirmation:
            errors.append("Las contraseñas no coinciden.")
        else:
            try:
                activate_access_invitation(
                    invitation_id=invitation.id,
                    token=token,
                    password=password,
                )
            except ValidationError as exc:
                errors.extend(exc.messages)
            else:
                return redirect("account-activation-complete")
    return render(
        request,
        "accounts/activate_invitation.html",
        {"invitation": invitation, "errors": errors},
    )


def activation_complete(request):
    return render(request, "accounts/activation_complete.html")
