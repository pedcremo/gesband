from django.contrib import admin

from .models import Activity, Attendance, Invitation, InvitationResponseEvent, ProgrammeItem

admin.site.register([Activity, ProgrammeItem, Invitation, InvitationResponseEvent, Attendance])
