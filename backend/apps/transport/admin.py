from django.contrib import admin

from .models import Transport, TransportAssignment

admin.site.register([Transport, TransportAssignment])
