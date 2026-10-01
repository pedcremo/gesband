from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class PanelLoginForm(AuthenticationForm):
    """Acceso al panel con el usuario o con el correo de la cuenta.

    Las cuentas creadas al aceptar una invitacion tienen un usuario interno que
    la persona no conoce; su credencial es el correo, igual que en la app.
    """

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = _("Correo electrónico o usuario")

    def clean(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        if "@" in identifier:
            matches = list(
                get_user_model().objects.filter(email__iexact=identifier).values_list("username", flat=True)[:2]
            )
            # Solo se traduce si el correo identifica una sola cuenta.
            if len(matches) == 1:
                self.cleaned_data["username"] = matches[0]
        return super().clean()
