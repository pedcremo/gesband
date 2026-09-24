from django.contrib import admin

from .models import Poll, PollOption, PollRecipient

# `Ballot` no se registra: listar papeletas junto a la participacion no revela
# nada que el recuento no diga ya, pero tampoco aporta nada a la operacion.
admin.site.register([Poll, PollOption, PollRecipient])
