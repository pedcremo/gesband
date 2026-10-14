"""Datos de presentación del asistente de importación del censo.

La previsualización del panel se calcula aquí, a la vista del catálogo actual
de la asociación del lote, para que muestre siempre qué cuerdas e instrumentos
se crearían y qué filas chocan con el catálogo. Solo lee; no crea nada.
"""

from django import template

from apps.members.forms import IMPORT_FIELD_CHOICES
from apps.members.models import ImportBatch
from apps.members.services import review_import, uses_catalog_columns

register = template.Library()


@register.simple_tag
def import_field_choices():
    return IMPORT_FIELD_CHOICES


@register.simple_tag
def import_review(batch):
    rows = list(batch.preview)
    uses_catalog = uses_catalog_columns(batch.mapping)
    new_sections = []
    new_instruments = []
    if uses_catalog and batch.status == ImportBatch.Status.PREVIEW:
        rows, plan = review_import(batch.association, rows)
        new_sections = list(plan.new_sections.values())
        new_instruments = plan.new_instrument_labels()
    elif uses_catalog and batch.status == ImportBatch.Status.CONFIRMED:
        new_sections = batch.result.get("sections_created", [])
        new_instruments = batch.result.get("instruments_created", [])
    return {
        "rows": rows,
        "uses_catalog": uses_catalog,
        "new_sections": new_sections,
        "new_instruments": new_instruments,
        "can_confirm": any(not item["errors"] for item in rows),
    }
