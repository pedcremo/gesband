"""Catálogo predefinido de cuerdas e instrumentos (decisión 0012).

Las cuerdas son comunes a todas las asociaciones y fijas: solo se amplían con
una migración. Los instrumentos pertenecen a cada asociación; esta lista es la
precarga que recibe cada banda, que después puede sumar los suyos.

No importa modelos: las migraciones de datos pasan sus modelos históricos.
Cada entrada lleva su nombre en castellano, valenciano e inglés y alias que la
importación también reconoce.
"""

import unicodedata

SECTIONS = [
    # (código, castellano, valenciano, inglés, alias)
    ("brass", "Viento metal", "Vent metall", "Brass", ["Metal", "Metales", "Metall", "Metalls"]),
    ("woodwind", "Viento madera", "Vent fusta", "Woodwind", ["Madera", "Maderas", "Fusta", "Woodwinds"]),
    ("percussion", "Percusión", "Percussió", "Percussion", []),
    (
        "bowed_strings",
        "Cuerda frotada",
        "Corda fregada",
        "Bowed strings",
        ["Cuerda", "Cuerdas", "Corda", "Cordes", "Strings", "Cuerda frotada", "Corda fregada"],
    ),
    ("struck_strings", "Cuerda percutida", "Corda percudida", "Struck strings", []),
    ("plucked_strings", "Cuerda pulsada", "Corda polsada", "Plucked strings", []),
]

INSTRUMENTS = [
    # (código, cuerda, castellano, valenciano, inglés, alias)
    ("piccolo", "woodwind", "Flautín", "Flautí", "Piccolo", ["Piccolo"]),
    ("flute", "woodwind", "Flauta", "Flauta", "Flute", ["Flauta travesera", "Flauta travessera"]),
    ("oboe", "woodwind", "Oboe", "Oboè", "Oboe", []),
    ("english_horn", "woodwind", "Corno inglés", "Corn anglés", "English horn", ["Cor anglais"]),
    ("bassoon", "woodwind", "Fagot", "Fagot", "Bassoon", []),
    ("contrabassoon", "woodwind", "Contrafagot", "Contrafagot", "Contrabassoon", []),
    ("eb_clarinet", "woodwind", "Requinto", "Requint", "E-flat clarinet", ["Clarinete requinto"]),
    ("clarinet", "woodwind", "Clarinete", "Clarinet", "Clarinet", []),
    ("bass_clarinet", "woodwind", "Clarinete bajo", "Clarinet baix", "Bass clarinet", []),
    ("soprano_saxophone", "woodwind", "Saxofón soprano", "Saxòfon soprano", "Soprano saxophone", ["Saxo soprano"]),
    ("alto_saxophone", "woodwind", "Saxofón alto", "Saxòfon alt", "Alto saxophone", ["Saxo alto", "Saxo alt"]),
    ("tenor_saxophone", "woodwind", "Saxofón tenor", "Saxòfon tenor", "Tenor saxophone", ["Saxo tenor"]),
    (
        "baritone_saxophone",
        "woodwind",
        "Saxofón barítono",
        "Saxòfon baríton",
        "Baritone saxophone",
        ["Saxo barítono", "Saxo baríton"],
    ),
    ("dulzaina", "woodwind", "Dulzaina", "Dolçaina", "Dulzaina", []),
    ("bagpipes", "woodwind", "Gaita", "Gaita", "Bagpipes", []),
    ("trumpet", "brass", "Trompeta", "Trompeta", "Trumpet", []),
    ("cornet", "brass", "Corneta", "Corneta", "Cornet", []),
    ("flugelhorn", "brass", "Fliscorno", "Fiscorn", "Flugelhorn", ["Fiscorno"]),
    ("french_horn", "brass", "Trompa", "Trompa", "French horn", ["Horn"]),
    ("trombone", "brass", "Trombón", "Trombó", "Trombone", []),
    ("bass_trombone", "brass", "Trombón bajo", "Trombó baix", "Bass trombone", []),
    ("euphonium", "brass", "Bombardino", "Bombardí", "Euphonium", []),
    ("tuba", "brass", "Tuba", "Tuba", "Tuba", []),
    ("sousaphone", "brass", "Sousáfono", "Sousàfon", "Sousaphone", []),
    ("snare_drum", "percussion", "Caja", "Caixa", "Snare drum", ["Caja clara"]),
    ("bass_drum", "percussion", "Bombo", "Bombo", "Bass drum", []),
    ("cymbals", "percussion", "Platos", "Plats", "Cymbals", []),
    ("timpani", "percussion", "Timbales", "Timbals", "Timpani", []),
    ("drum_kit", "percussion", "Batería", "Bateria", "Drum kit", []),
    ("mallets", "percussion", "Láminas", "Làmines", "Mallet percussion", []),
    ("xylophone", "percussion", "Xilófono", "Xilòfon", "Xylophone", []),
    ("marimba", "percussion", "Marimba", "Marimba", "Marimba", []),
    ("vibraphone", "percussion", "Vibráfono", "Vibràfon", "Vibraphone", []),
    ("glockenspiel", "percussion", "Glockenspiel", "Glockenspiel", "Glockenspiel", ["Lira"]),
    ("tubular_bells", "percussion", "Campanas tubulares", "Campanes tubulars", "Tubular bells", []),
    ("tabalet", "percussion", "Tabalet", "Tabalet", "Tabalet", []),
    ("auxiliary_percussion", "percussion", "Pequeña percusión", "Percussió menuda", "Auxiliary percussion", []),
    ("violin", "bowed_strings", "Violín", "Violí", "Violin", []),
    ("viola", "bowed_strings", "Viola", "Viola", "Viola", []),
    ("cello", "bowed_strings", "Violonchelo", "Violoncel", "Cello", ["Violoncelo", "Chelo"]),
    ("double_bass", "bowed_strings", "Contrabajo", "Contrabaix", "Double bass", []),
    ("piano", "struck_strings", "Piano", "Piano", "Piano", []),
    ("hammered_dulcimer", "struck_strings", "Dulcémele", "Dulcèmel", "Hammered dulcimer", ["Salterio"]),
    ("harp", "plucked_strings", "Arpa", "Arpa", "Harp", []),
    ("guitar", "plucked_strings", "Guitarra", "Guitarra", "Guitar", []),
    ("electric_bass", "plucked_strings", "Bajo eléctrico", "Baix elèctric", "Electric bass", []),
    ("bandurria", "plucked_strings", "Bandurria", "Bandúrria", "Bandurria", []),
    ("lute", "plucked_strings", "Laúd", "Llaüt", "Lute", []),
    ("mandolin", "plucked_strings", "Mandolina", "Mandolina", "Mandolin", []),
    ("harpsichord", "plucked_strings", "Clavecín", "Clavicèmbal", "Harpsichord", []),
]


def section_names(entry):
    code, es, ca, en, aliases = entry
    return [code, es, ca, en, *aliases]


def instrument_names(entry):
    code, _section, es, ca, en, aliases = entry
    return [code, es, ca, en, *aliases]


def catalog_key(value):
    """Clave para comparar nombres sin distinguir mayúsculas, acentos ni espacios."""
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", str(value))
        if not unicodedata.combining(character)
    )
    return "".join(without_accents.casefold().split())


def section_codes_by_key():
    """Clave de cualquier nombre o alias de cuerda -> código."""
    return {catalog_key(name): entry[0] for entry in SECTIONS for name in section_names(entry)}


def instruments_by_key():
    """Clave de cualquier nombre o alias de instrumento -> entrada del catálogo."""
    return {catalog_key(name): entry for entry in INSTRUMENTS for name in instrument_names(entry)}


def seed_sections(section_model):
    """Crea o actualiza las cuerdas fijas. Idempotente."""
    for order, (code, es, ca, en, _aliases) in enumerate(SECTIONS, start=1):
        section_model.objects.update_or_create(
            code=code, defaults={"name": es, "name_ca": ca, "name_en": en, "order": order}
        )


def seed_instruments(association, instrument_model, section_model):
    """Añade a la asociación los instrumentos predefinidos que le falten.

    Idempotente. Un instrumento propio que ya se llama como uno del catálogo
    (en cualquier idioma o alias) se vincula a él en lugar de duplicarse; su
    nombre no cambia y su cuerda solo se rellena si no tenía. Devuelve cuántos
    instrumentos se crearon.
    """
    sections = {section.code: section for section in section_model.objects.all()}
    existing = list(instrument_model.objects.filter(association=association).order_by("pk"))
    used_codes = {instrument.code for instrument in existing if instrument.code}
    by_key = {}
    for instrument in existing:
        for name in (instrument.name, instrument.name_ca, instrument.name_en):
            if name:
                by_key.setdefault(catalog_key(name), instrument)
    created = 0
    for entry in INSTRUMENTS:
        code, section_code, es, ca, en, _aliases = entry
        if code in used_codes:
            continue
        match = next(
            (by_key[key] for key in map(catalog_key, instrument_names(entry)) if key in by_key and not by_key[key].code),
            None,
        )
        if match is not None:
            match.code = code
            match.name_ca = match.name_ca or ca
            match.name_en = match.name_en or en
            if match.section_id is None:
                match.section = sections.get(section_code)
            match.save(update_fields=["code", "name_ca", "name_en", "section"])
        elif catalog_key(es) not in by_key:
            instrument_model.objects.create(
                association=association, code=code, name=es, name_ca=ca, name_en=en, section=sections.get(section_code)
            )
            created += 1
        used_codes.add(code)
    return created
