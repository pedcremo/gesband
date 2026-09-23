from django.contrib import admin

from .models import ImportBatch, Instrument, Member, MemberInstrument, Section

admin.site.register([Section, Instrument, Member, MemberInstrument, ImportBatch])
