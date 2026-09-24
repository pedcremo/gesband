from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Exists, OuterRef
from rest_framework import decorators, response, serializers, status

from apps.api import ScopedViewSet
from apps.associations.models import AssociationAccess
from apps.associations.permissions import MANAGER_ROLES

from . import services
from .models import Poll, PollRecipient


def _is_manager(request, association_id):
    if request.user.is_superuser:
        return True
    access = AssociationAccess.objects.filter(
        account=request.user, association_id=association_id, is_active=True
    ).first()
    roles = set(access.role_assignments.values_list("role", flat=True)) if access else set()
    return bool(roles.intersection(MANAGER_ROLES))


class PollSerializer(serializers.ModelSerializer):
    options = serializers.ListField(child=serializers.CharField(max_length=200), write_only=True, required=False)
    choices = serializers.SerializerMethodField()
    results = serializers.SerializerMethodField()
    participation = serializers.SerializerMethodField()
    has_voted = serializers.SerializerMethodField()
    can_vote = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = [
            "id",
            "association",
            "question",
            "description",
            "status",
            "closes_at",
            "opened_at",
            "published_at",
            "cancelled_at",
            "cancel_reason",
            "options",
            "choices",
            "results",
            "participation",
            "has_voted",
            "can_vote",
            "recipients",
        ]
        read_only_fields = [
            "id",
            "association",
            "status",
            "opened_at",
            "published_at",
            "cancelled_at",
            "cancel_reason",
        ]

    def _manager(self):
        return self.context.get("is_manager", False)

    def _own_recipient(self, obj):
        request = self.context.get("request")
        cache = self.context.setdefault("_own_recipient", {})
        if obj.pk not in cache:
            cache[obj.pk] = PollRecipient.objects.filter(poll=obj, member__account=request.user).first()
        return cache[obj.pk]

    def _tally(self, obj):
        cache = self.context.setdefault("_tally", {})
        if obj.pk not in cache:
            cache[obj.pk] = services.tally(obj)
        return cache[obj.pk]

    def get_choices(self, obj):
        return [{"id": option.id, "label": option.label} for option in obj.options.all()]

    def get_results(self, obj):
        visibility = services.result_visibility(obj, is_manager=self._manager())
        if not visibility:
            return None
        summary = self._tally(obj)
        return {"kind": visibility, "votes_cast": summary["votes_cast"], "options": summary["options"]}

    def get_participation(self, obj):
        summary = self._tally(obj)
        return {"recipients": summary["recipients"], "voted": summary["voted"]}

    def get_has_voted(self, obj):
        recipient = self._own_recipient(obj)
        return recipient.has_voted if recipient else None

    def get_can_vote(self, obj):
        recipient = self._own_recipient(obj)
        return bool(recipient and not recipient.has_voted and obj.is_voting_open)

    def get_recipients(self, obj):
        """Quien ha votado, solo para la junta y solo con la votacion cerrada.

        Mientras se vota, ver a la vez quien acaba de votar y como se mueve el
        recuento provisional bastaria para deducir el voto de cada cual.
        """
        if not self._manager() or obj.is_voting_open:
            return None
        return [
            {"member": recipient.member_id, "member_name": str(recipient.member), "has_voted": recipient.has_voted}
            for recipient in obj.recipients.select_related("member").order_by("member__last_name", "member__first_name")
        ]

    def create(self, validated_data):
        return services.create_poll(
            association=self.context["association"],
            account=self.context["request"].user,
            question=validated_data.get("question"),
            description=validated_data.get("description", ""),
            closes_at=validated_data.get("closes_at"),
            options=validated_data.get("options", []),
        )

    def update(self, instance, validated_data):
        return services.update_draft(
            instance,
            question=validated_data.get("question"),
            description=validated_data.get("description"),
            closes_at=validated_data.get("closes_at"),
            options=validated_data.get("options"),
        )


class PollViewSet(ScopedViewSet):
    serializer_class = PollSerializer
    ordering = ("-closes_at", "id")
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def association_id(self):
        value = (
            self.request.headers.get("X-Association-ID")
            or self.request.query_params.get("association_id")
            or self.request.data.get("association")
        )
        if value:
            return value
        poll_id = self.kwargs.get("pk")
        if poll_id:
            try:
                poll = Poll.objects.filter(pk=poll_id).only("association_id").first()
            except DjangoValidationError:
                poll = None
            if poll:
                return poll.association_id
        return super().association_id()

    def is_manager(self):
        return _is_manager(self.request, self.association_id())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["is_manager"] = self.is_manager()
        return context

    def get_queryset(self):
        association_id = self.association_id()
        self.check_access()
        queryset = Poll.objects.filter(association_id=association_id)
        if not self.is_manager():
            # Una anulada en borrador nunca se anuncio: no hay nada que mostrar.
            mine = PollRecipient.objects.filter(poll=OuterRef("pk"), member__account=self.request.user)
            queryset = queryset.filter(Exists(mine), opened_at__isnull=False).exclude(status=Poll.Status.DRAFT)
        return queryset.prefetch_related("options")

    def create(self, request, *args, **kwargs):
        # El permiso antes que la validacion: a quien no puede crear no se le
        # explica que le falta un campo.
        self.access = self.check_access(manager=True)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.check_access(manager=True)
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.context["association"] = self.access.association
        serializer.save()

    def perform_destroy(self, instance):
        self.check_access(manager=True)
        services.delete_draft(instance)

    def _detail(self, poll, http_status=status.HTTP_200_OK):
        poll.refresh_from_db()
        return response.Response(self.get_serializer(poll).data, status=http_status)

    @decorators.action(detail=True, methods=["post"])
    def recipients(self, request, pk=None):
        self.check_access(manager=True)
        poll = self.get_object()
        data = request.data
        members = services.eligible_members(
            poll.association,
            member_ids=data.get("member_ids") or [],
            instrument_ids=data.get("instrument_ids") or [],
            section_ids=data.get("section_ids") or [],
            all_active_musicians=bool(data.get("all_active_musicians", False)),
        )
        return response.Response({"recipients": services.set_recipients(poll, members)})

    @decorators.action(detail=True, methods=["post"], url_path="open")
    def open_voting(self, request, pk=None):
        self.check_access(manager=True)
        result = services.open_poll(self.get_object(), request.user)
        return self._detail(result["poll"])

    @decorators.action(detail=True, methods=["post"])
    def vote(self, request, pk=None):
        self.check_access()
        poll = self.get_object()
        services.cast_vote(poll, request.user, request.data.get("option_id"))
        return self._detail(poll, status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        self.check_access(manager=True)
        result = services.publish_results(self.get_object(), request.user)
        return self._detail(result["poll"])

    @decorators.action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self.check_access(manager=True)
        result = services.cancel_poll(self.get_object(), request.user, request.data.get("reason", ""))
        return self._detail(result["poll"])
