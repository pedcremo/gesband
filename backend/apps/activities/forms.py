from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import Activity, ProgrammeItem


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


class ActivityCreateForm(ActivityChangeForm):
    """Alta de una actividad desde el panel; nace en borrador.

    La vista entrega una instancia con asociación, autor y estado ya fijados,
    de modo que la validación del modelo (`Activity.clean`) se aplica completa.
    El repertorio se escribe como un título por línea; lo que siga a una barra
    vertical se guarda como nota de esa obra.
    """

    programme = forms.CharField(
        label=_("Repertorio"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text=_("Opcional. Un título por línea; añade notas tras «|», p. ej. «Paquito el chocolatero | de pasacalle»."),
    )

    class Meta(ActivityChangeForm.Meta):
        fields = ["kind", *ActivityChangeForm.Meta.fields]

    def clean_programme(self):
        title_limit = ProgrammeItem._meta.get_field("title").max_length
        items = []
        for number, line in enumerate(self.cleaned_data["programme"].splitlines(), start=1):
            title, _separator, notes = line.partition("|")
            title, notes = title.strip(), notes.strip()
            if not title:
                if notes:
                    raise forms.ValidationError(_("La línea %(line)s tiene notas pero no título.") % {"line": number})
                continue
            if len(title) > title_limit:
                raise forms.ValidationError(
                    _("El título de la línea %(line)s supera los %(limit)s caracteres.")
                    % {"line": number, "limit": title_limit}
                )
            items.append((title, notes))
        return items

    @transaction.atomic
    def save(self, commit=True):
        activity = super().save(commit=commit)
        if commit:
            ProgrammeItem.objects.bulk_create(
                ProgrammeItem(activity=activity, title=title, notes=notes, order=order)
                for order, (title, notes) in enumerate(self.cleaned_data["programme"])
            )
        return activity
