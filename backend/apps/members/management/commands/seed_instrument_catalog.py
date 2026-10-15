"""Precarga las cuerdas comunes y los instrumentos predefinidos (decisión 0012).

Idempotente: las migraciones ya lo hacen al desplegar; sirve para llevar a las
bandas existentes los instrumentos que se añadan después a `catalog.py`.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.associations.models import Association
from apps.members.catalog import seed_sections
from apps.members.models import Section
from apps.members.services import seed_default_instruments


class Command(BaseCommand):
    help = "Crea las cuerdas comunes y añade a cada asociación los instrumentos predefinidos que le falten."

    def add_arguments(self, parser):
        parser.add_argument("--association", help="Identificador para URL (slug) de una sola asociación.")

    def handle(self, *args, association=None, **options):
        seed_sections(Section)
        associations = Association.objects.order_by("name")
        if association:
            associations = associations.filter(slug__iexact=association)
            if not associations.exists():
                raise CommandError(f"No existe la asociación «{association}».")
        for item in associations:
            created = seed_default_instruments(item)
            self.stdout.write(f"{item.slug}: {created} instrumentos añadidos.")
