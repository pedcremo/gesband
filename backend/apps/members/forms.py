"""Formularios del panel para mantener fichas del censo (decisión 0009).

Recogen y validan la forma de los datos. Las reglas de permiso, asociación y
unicidad viven en `apps/members/services.py`, que también usa la API.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Instrument, Member, MemberPosition


class MemberForm(forms.ModelForm):
    """Datos de la ficha, instrumentos (con su cuerda) y cargos registrables."""

    instruments = forms.ModelMultipleChoiceField(
        label=_("Instrumentos"),
        queryset=Instrument.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    primary_instrument = forms.ModelChoiceField(
        label=_("Instrumento principal"),
        queryset=Instrument.objects.none(),
        required=False,
        help_text=_("Su cuerda es la del instrumento principal."),
    )
    positions = forms.MultipleChoiceField(
        label=_("Cargos"),
        choices=MemberPosition.Position.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Los cargos son informativos: no conceden permisos en Gesband. Los permisos se dan con roles."),
    )

    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "external_id",
            "kind",
            "status",
            "email",
            "phone",
            "address",
            "national_id",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}
        help_texts = {
            "external_id": _("Número de socio u otro identificador estable de la asociación. Opcional."),
            "national_id": _("Opcional. Pídelo solo si la asociación lo necesita."),
            "status": _("Una ficha inactiva está de baja: no se convoca, pero conserva su historial."),
        }

    def __init__(self, *args, association, **kwargs):
        super().__init__(*args, **kwargs)
        self.association = association
        instruments = Instrument.objects.filter(association=association).select_related("section")
        self.fields["instruments"].queryset = instruments
        self.fields["primary_instrument"].queryset = instruments
        self.fields["instruments"].label_from_instance = _instrument_label
        self.fields["primary_instrument"].label_from_instance = _instrument_label
        if self.instance.pk:
            selected = list(self.instance.member_instruments.all())
            self.initial.setdefault("instruments", [item.instrument_id for item in selected])
            primary = next((item.instrument_id for item in selected if item.is_primary), None)
            self.initial.setdefault("primary_instrument", primary)
            self.initial.setdefault("positions", list(self.instance.positions.values_list("position", flat=True)))

    def validate_unique(self):
        # La unicidad por asociación la comprueba el servicio, que conoce la
        # asociación de la ficha; aquí la instancia todavía no la tiene.
        pass

    def member_data(self):
        """Campos de la ficha para el servicio, sin instrumentos ni cargos."""
        return {field: self.cleaned_data[field] for field in self.Meta.fields}


def _instrument_label(instrument):
    if instrument.section_id:
        return f"{instrument.name} ({instrument.section.name})"
    return instrument.name


class PhotoForm(forms.Form):
    photo = forms.FileField(
        label=_("Foto"),
        help_text=_("JPEG, PNG o WebP, hasta 5 MB. Se eliminan los metadatos y solo la ven la persona y la junta."),
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
    )

