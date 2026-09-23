from django.contrib import admin

from .models import Association, AssociationAccess, AssociationRole

admin.site.register([Association, AssociationAccess, AssociationRole])
