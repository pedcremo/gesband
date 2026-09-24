"""Formularios del panel de la junta para las encuestas.

Solo recogen y dan forma a los datos. Las reglas (número de opciones, plazos,
quién puede ser destinatario) viven en `apps/polls/services.py`.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.activities.forms import DateTimeLocalInput
from apps.members.models import Instrument, Member, Section


class PollForm(forms.Form):
    """Enunciado, descripción, cierre y opciones de un borrador."""

    question = forms.CharField(label=_("Enunciado"), max_length=300)
    description = forms.CharField(
        label=_("Descripción"), required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    closes_at = forms.DateTimeField(
        label=_("Cierre de la votación"),
        widget=DateTimeLocalInput(),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"],
    )
    options = forms.CharField(
        label=_("Opciones"),
        help_text=_("Una por línea. Hacen falta al menos dos."),
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    @classmethod
    def for_poll(cls, poll, data=None):
        initial = {
            "question": poll.question,
            "description": poll.description,
            "closes_at": poll.closes_at,
            "options": "\n".join(option.label for option in poll.options.all()),
        }
        return cls(data, initial=initial)

    def option_labels(self):
        """Una opción por línea; las líneas vacías se descartan en el servicio."""
        return self.cleaned_data["options"].splitlines()


class LenientMultipleChoiceField(forms.MultipleChoiceField):
    """Casillas que descartan en silencio los valores que no se ofrecieron.

    Un identificador de otra asociación, o uno mal formado, se ignora en lugar
    de invalidar toda la selección.
    """

    def to_python(self, value):
        offered = {str(key) for key, _label in self.choices}
        return [item for item in super().to_python(value) if item in offered]

    def validate(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages["required"], code="required")


class RecipientSelectionForm(forms.Form):
    """Destinatarios por músicos activos, cuerdas, instrumentos o personas."""

    all_active_musicians = forms.BooleanField(label=_("Todos los músicos activos"), required=False)
    section_ids = LenientMultipleChoiceField(
        label=_("Cuerdas"), required=False, widget=forms.CheckboxSelectMultiple
    )
    instrument_ids = LenientMultipleChoiceField(
        label=_("Instrumentos"), required=False, widget=forms.CheckboxSelectMultiple
    )
    member_ids = LenientMultipleChoiceField(
        label=_("Personas"), required=False, widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, association, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section_ids"].choices = [
            (str(section.pk), section.name) for section in Section.objects.filter(association=association)
        ]
        self.fields["instrument_ids"].choices = [
            (str(instrument.pk), instrument.name)
            for instrument in Instrument.objects.filter(association=association)
        ]
        self.fields["member_ids"].choices = [
            (str(member.pk), str(member))
            for member in Member.objects.filter(association=association, status=Member.Status.ACTIVE).order_by(
                "last_name", "first_name"
            )
        ]
