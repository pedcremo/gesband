from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Activity


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def format_value(self, value):
        return value.strftime("%Y-%m-%dT%H:%M") if hasattr(value, "strftime") else value


class ActivityChangeForm(forms.ModelForm):
    """Cambios de la ficha que la junta hace desde el panel.

    Solo expone los campos que la persona convocada necesita conocer; el estado
    se cambia con publicar o cancelar, que avisan por su cuenta.
    """

    class Meta:
        model = Activity
        fields = [
            "title",
            "starts_at",
            "ends_at",
            "meeting_at",
            "location",
            "uniform",
            "response_deadline",
            "is_mandatory",
            "description",
        ]
        widgets = {
            "starts_at": DateTimeLocalInput(),
            "ends_at": DateTimeLocalInput(),
            "meeting_at": DateTimeLocalInput(),
            "response_deadline": DateTimeLocalInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {"is_mandatory": _("Asistencia obligatoria")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ["starts_at", "ends_at", "meeting_at", "response_deadline"]:
            self.fields[name].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]
