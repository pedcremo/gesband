from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Association


class BrandingForm(forms.ModelForm):
    logo = forms.ImageField(
        label=_("Logo"),
        required=False,
        help_text=_("PNG, JPG o WebP de hasta 2 MB. Se recorta en un cuadrado con esquinas redondeadas."),
    )
    remove_logo = forms.BooleanField(label=_("Quitar el logo y usar las iniciales"), required=False)

    class Meta:
        model = Association
        fields = ["motto", "primary_color", "secondary_color", "visual_style", "color_mode"]
        widgets = {
            "primary_color": forms.TextInput(attrs={"type": "color"}),
            "secondary_color": forms.TextInput(attrs={"type": "color"}),
            "visual_style": forms.RadioSelect,
            "color_mode": forms.RadioSelect,
        }
        help_texts = {
            "primary_color": _("Cualquier color: el panel y la app ajustan el texto para que se lea."),
            "color_mode": _("Cada persona puede cambiarlo en su dispositivo."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El widget de color del navegador siempre envía minúsculas; el modelo guarda mayúsculas.
        for field in ("primary_color", "secondary_color"):
            if self.initial.get(field):
                self.initial[field] = self.initial[field].lower()
