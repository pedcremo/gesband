from django.contrib import admin

from .models import Delivery, DeviceRegistration, Notification

admin.site.register([Notification, DeviceRegistration, Delivery])
