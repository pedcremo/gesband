from django.db import migrations

from apps.members import catalog


def forwards(apps, schema_editor):
    """Fusiona las cuerdas de cada asociación en las seis comunes y precarga instrumentos.

    Cada instrumento existente toma la cuerda del catálogo si su nombre es uno
    de los predefinidos; si no, la que corresponda al nombre de su cuerda
    antigua (Metal, Madera, Corda...). Si ninguna encaja, queda sin cuerda.
    """
    Association = apps.get_model("associations", "Association")
    Instrument = apps.get_model("members", "Instrument")
    Section = apps.get_model("members", "Section")

    catalog.seed_sections(Section)
    global_sections = {section.code: section for section in Section.objects.filter(association__isnull=True)}
    section_codes = catalog.section_codes_by_key()
    known_instruments = catalog.instruments_by_key()
    for instrument in Instrument.objects.select_related("section"):
        entry = known_instruments.get(catalog.catalog_key(instrument.name))
        if entry is not None:
            code = entry[1]
        elif instrument.section_id:
            code = section_codes.get(catalog.catalog_key(instrument.section.name))
        else:
            code = None
        instrument.section = global_sections.get(code)
        instrument.save(update_fields=["section"])
    Section.objects.filter(association__isnull=False).delete()

    for association in Association.objects.all():
        catalog.seed_instruments(association, Instrument, Section)


def backwards(apps, schema_editor):
    """Vuelve a cuerdas por asociación con el nombre en castellano de las comunes.

    Los instrumentos precargados se conservan; sus códigos y traducciones
    desaparecen al deshacer la migración 0005.
    """
    Instrument = apps.get_model("members", "Instrument")
    Section = apps.get_model("members", "Section")
    for instrument in Instrument.objects.filter(section__association__isnull=True).select_related("section"):
        local, _created = Section.objects.get_or_create(
            association_id=instrument.association_id,
            name=instrument.section.name,
            defaults={"order": instrument.section.order},
        )
        instrument.section = local
        instrument.save(update_fields=["section"])
    Section.objects.filter(association__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("associations", "0003_association_visual_style"),
        ("members", "0005_global_sections_schema"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
