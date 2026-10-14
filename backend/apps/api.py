import mimetypes
from datetime import timezone as dt_timezone
from contextlib import contextmanager

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.activities.models import Activity, Attendance, Invitation, ProgrammeItem, remuneration_error
from apps.activities.payments import member_earnings
from apps.activities.services import record_attendance, respond
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.associations.permissions import MANAGER_ROLES, PARTICIPANT_ROLES, accessible_association_ids, get_access_or_403, permissions_for, require_roles
from apps.communications.models import Notification
from apps.communications.services import revoke_account_devices
from apps.members import services as member_services
from apps.members.models import ImportBatch, Instrument, Member, MemberInstrument, Section
from apps.members.services import confirm_import, parse_import
from apps.transport.models import Transport, TransportAssignment

from rest_framework import serializers


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    display_name = serializers.SerializerMethodField()
    email = serializers.EmailField()

    def get_display_name(self, obj):
        return obj.get_full_name() or obj.email


class AssociationSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Association
        fields = [
            "id",
            "name",
            "slug",
            "logo_url",
            "primary_color",
            "secondary_color",
            "motto",
            "visual_style",
            "color_mode",
            "timezone",
            "permissions",
        ]

    def get_logo_url(self, obj):
        """El logotipo vive en media privada: se sirve por la API, como la foto del musico."""
        request = self.context.get("request")
        if obj.logo and request:
            return request.build_absolute_uri(f"/api/v1/associations/{obj.pk}/logo/")
        return None

    def get_permissions(self, obj):
        request = self.context.get("request")
        if not request:
            return []
        return permissions_for(request.user, obj)


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "name", "order"]


class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ["id", "name", "section"]

    def validate_section(self, section):
        association_id = self.context.get("association_id")
        if section and association_id and str(section.association_id) != str(association_id):
            raise serializers.ValidationError(_("La cuerda pertenece a otra asociación."))
        return section


class MemberSerializer(serializers.ModelSerializer):
    instruments = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ["id", "external_id", "first_name", "last_name", "national_id", "address", "phone", "email", "kind", "status", "photo_url", "instruments", "account"]
        read_only_fields = ["id", "photo_url", "account"]

    def get_instruments(self, obj):
        return [{"id": x.instrument_id, "name": x.instrument.name, "is_primary": x.is_primary} for x in obj.member_instruments.select_related("instrument")]

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if not obj.photo or not request:
            return None
        if self.context.get("own_profile"):
            # La ficha propia se descarga por /members/me/photo/: la ruta por id
            # exige gestionar el censo y daria 403 al musico. La asociacion va en
            # la consulta para que la URL funcione tambien sin la cabecera.
            return request.build_absolute_uri(f"/api/v1/members/me/photo/?association_id={obj.association_id}")
        return request.build_absolute_uri(f"/api/v1/members/{obj.pk}/photo/")


class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgrammeItem
        fields = ["id", "title", "notes", "order"]


class InvitationSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    attendance = serializers.SerializerMethodField()
    needs_reconfirmation = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = [
            "id",
            "member",
            "member_name",
            "response",
            "response_note",
            "responded_at",
            "activity_version",
            "needs_reconfirmation",
            "attendance",
        ]
        read_only_fields = ["responded_at", "activity_version", "needs_reconfirmation", "attendance"]

    def get_needs_reconfirmation(self, obj):
        """Pendiente con respuestas anteriores: un cambio anulo lo ya contestado.

        Sin esto el cliente no distingue «no he contestado todavia» de «me han
        anulado el si porque cambio la fecha».
        """
        if obj.response != Invitation.Response.PENDING:
            return False
        return obj.response_history.exists()

    def get_member_name(self, obj):
        return str(obj.member)

    def get_attendance(self, obj):
        try:
            return {"status": obj.attendance.status, "note": obj.attendance.note}
        except Attendance.DoesNotExist:
            return {"status": Attendance.Status.UNRECORDED, "note": ""}


class MyTransportSerializer(serializers.ModelSerializer):
    """Lo que el musico necesita de su transporte; sin datos de los demas ocupantes."""

    transport_id = serializers.UUIDField(source="transport.id")
    kind = serializers.CharField(source="transport.kind")
    label = serializers.CharField(source="transport.label")
    meeting_point = serializers.CharField(source="transport.meeting_point")
    departure_at = serializers.DateTimeField(source="transport.departure_at")
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = TransportAssignment
        fields = ["id", "transport_id", "member", "kind", "label", "meeting_point", "departure_at", "driver_name"]

    def get_driver_name(self, obj):
        return str(obj.transport.driver) if obj.transport.driver_id else None


class ActivitySerializer(serializers.ModelSerializer):
    programme = ProgrammeSerializer(many=True, required=False)
    invitations = serializers.SerializerMethodField()
    my_invitation = serializers.SerializerMethodField()
    my_transport = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ["id", "association", "kind", "status", "title", "description", "location", "starts_at", "ends_at", "meeting_at", "response_deadline", "uniform", "is_mandatory", "is_paid", "fee_amount", "version", "programme", "invitations", "my_invitation", "my_transport"]
        # `status` solo cambia por las acciones publish y cancel, que avisan a
        # quien esta convocado; un PATCH lo cambiaria en silencio.
        read_only_fields = ["id", "association", "created_by", "status", "version", "invitations"]

    def validate(self, attrs):
        """Remunerada exige importe positivo; no remunerada guarda el importe vacio.

        La regla es la del modelo (`remuneration_error`), compartida con el panel.
        """
        attrs = super().validate(attrs)
        is_paid = attrs.get("is_paid", getattr(self.instance, "is_paid", False))
        fee_amount = attrs.get("fee_amount", getattr(self.instance, "fee_amount", None))
        error = remuneration_error(is_paid, fee_amount)
        if error:
            raise serializers.ValidationError({"fee_amount": error})
        if not is_paid:
            attrs["fee_amount"] = None
        return attrs

    def create(self, validated_data):
        programme = validated_data.pop("programme", [])
        association_id = self.context["association_id"]
        activity = Activity.objects.create(association_id=association_id, created_by=self.context["request"].user, **validated_data)
        ProgrammeItem.objects.bulk_create([ProgrammeItem(activity=activity, **item) for item in programme])
        return activity

    def get_invitations(self, obj):
        request = self.context.get("request")
        if not request:
            return []
        invitations = obj.invitations.all()
        access = AssociationAccess.objects.filter(account=request.user, association=obj.association, is_active=True).first()
        roles = set(access.role_assignments.values_list("role", flat=True)) if access else set()
        if not request.user.is_superuser and not roles.intersection(MANAGER_ROLES):
            invitations = invitations.filter(member__account=request.user)
        return InvitationSerializer(invitations, many=True, context=self.context).data

    def _own_invitation(self, obj):
        """La convocatoria de quien consulta, tambien si gestiona la banda."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return next((item for item in obj.invitations.all() if item.member.account_id == request.user.pk), None)

    def get_my_invitation(self, obj):
        invitation = self._own_invitation(obj)
        return InvitationSerializer(invitation, context=self.context).data if invitation else None

    def get_my_transport(self, obj):
        invitation = self._own_invitation(obj)
        if not invitation:
            return None
        assignment = (
            TransportAssignment.objects.filter(transport__activity=obj, member=invitation.member)
            .select_related("transport__driver")
            .first()
        )
        return MyTransportSerializer(assignment).data if assignment else None

    def update(self, instance, validated_data):
        from apps.activities.services import announce_activity_change, changed_activity_fields

        programme = validated_data.pop("programme", None)
        changed = changed_activity_fields(instance, validated_data)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.version += 1
        instance.full_clean()
        instance.save()
        if programme is not None:
            instance.programme.all().delete()
            ProgrammeItem.objects.bulk_create([ProgrammeItem(activity=instance, **item) for item in programme])
        self.change_notice = announce_activity_change(instance, changed, self.context["request"].user)
        return instance


class TransportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transport
        fields = ["id", "activity", "kind", "label", "meeting_point", "departure_at", "capacity", "driver"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        association_id = self.context.get("association_id")
        activity = attrs.get("activity", getattr(self.instance, "activity", None))
        driver = attrs.get("driver", getattr(self.instance, "driver", None))
        if activity and association_id and str(activity.association_id) != str(association_id):
            raise serializers.ValidationError({"activity": _("La actividad pertenece a otra asociación.")})
        if driver and association_id and str(driver.association_id) != str(association_id):
            raise serializers.ValidationError({"driver": _("El conductor pertenece a otra asociación.")})
        return attrs


class TransportAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportAssignment
        fields = ["id", "transport", "member"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        association_id = self.context.get("association_id")
        transport = attrs.get("transport", getattr(self.instance, "transport", None))
        member = attrs.get("member", getattr(self.instance, "member", None))
        if transport and association_id and str(transport.activity.association_id) != str(association_id):
            raise serializers.ValidationError({"transport": _("El transporte pertenece a otra asociación.")})
        if member and association_id and str(member.association_id) != str(association_id):
            raise serializers.ValidationError({"member": _("El miembro pertenece a otra asociación.")})
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "deep_link", "activity", "poll", "read_at", "created_at"]
        read_only_fields = fields


class LoginView(APIView):
    # Sin autenticacion: si el navegador trae la cookie del panel,
    # SessionAuthentication exigiria CSRF a un formulario que no lo necesita.
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        password = request.data.get("password", "")
        account_record = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
        account = authenticate(request, username=account_record.username if account_record else email, password=password)
        if not account:
            return response.Response({"detail": _("Credenciales no válidas.")}, status=401)
        token, _created = Token.objects.get_or_create(user=account)
        return response.Response({"access_token": token.key, "refresh_token": token.key, "token_type": "Bearer", "expires_in": 86400, "account": AccountSerializer(account).data})


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token_key = request.data.get("refresh_token")
        try:
            token = Token.objects.select_related("user").get(key=token_key)
        except Token.DoesNotExist as exc:
            raise ValidationError(_("Token de renovación no válido.")) from exc
        return response.Response({"access_token": token.key, "refresh_token": token.key, "token_type": "Bearer", "expires_in": 86400})


class MeView(APIView):
    def get(self, request):
        associations = Association.objects.filter(id__in=accessible_association_ids(request.user))
        return response.Response({"account": AccountSerializer(request.user).data, "associations": AssociationSerializer(associations, many=True, context={"request": request}).data})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        revoke_account_devices(request.user)
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class AssociationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssociationSerializer
    ordering = ("name", "id")

    def get_queryset(self):
        return Association.objects.filter(id__in=accessible_association_ids(self.request.user), is_active=True)

    @decorators.action(detail=True, methods=["get"], url_path="logo")
    def logo(self, request, pk=None):
        """Solo lo ve quien pertenece a la asociacion: `get_queryset` ya filtra por acceso."""
        association = self.get_object()
        if not association.logo:
            return response.Response(status=404)
        from django.http import FileResponse

        content_type = mimetypes.guess_type(association.logo.name)[0] or "application/octet-stream"
        return FileResponse(association.logo.open("rb"), content_type=content_type)


class ScopedViewSet(viewsets.ModelViewSet):
    association_kwarg = "association_id"
    manager_roles = MANAGER_ROLES

    def association_id(self):
        value = self.request.headers.get("X-Association-ID") or self.request.query_params.get("association_id") or self.request.data.get("association")
        if not value:
            raise ValidationError({"association_id": _("Es obligatorio seleccionar la asociación.")})
        return value

    def check_access(self, manager=False):
        return require_roles(self.request.user, self.association_id(), self.manager_roles if manager else PARTICIPANT_ROLES)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "association_id": self.association_id()}

    def perform_update(self, serializer):
        self.check_access(manager=True)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_access(manager=True)
        instance.delete()


class MemberViewSet(ScopedViewSet):
    serializer_class = MemberSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    ordering = ("last_name", "first_name", "id")

    def get_queryset(self):
        association_id = self.association_id()
        self.check_access(manager=True)
        return Member.objects.filter(association_id=association_id).prefetch_related("member_instruments__instrument")

    # Altas, cambios, bajas y borrados pasan por `apps.members.services`, que
    # tambien usa el panel (decision 0009).
    def perform_create(self, serializer):
        access = self.check_access(manager=True)
        with _domain_errors():
            serializer.instance = member_services.create_member(
                association=access.association, actor=self.request.user, data=serializer.validated_data
            )

    def perform_update(self, serializer):
        self.check_access(manager=True)
        with _domain_errors():
            serializer.instance = member_services.update_member(
                member=serializer.instance, actor=self.request.user, data=serializer.validated_data
            )

    def perform_destroy(self, instance):
        with _domain_errors(conflict=True):
            member_services.delete_member(member=instance, actor=self.request.user)

    @decorators.action(detail=True, methods=["get", "put", "delete"], url_path="photo")
    def photo(self, request, pk=None):
        member = self.get_object()
        if request.method == "GET":
            return _photo_response(member)
        if request.method == "DELETE":
            member_services.delete_member_photo(member=member, actor=request.user)
            return response.Response(status=204)
        if "photo" not in request.FILES:
            raise ValidationError({"photo": _("Adjunta una imagen.")})
        with _domain_errors(field="photo"):
            member = member_services.replace_member_photo(member=member, actor=request.user, upload=request.FILES["photo"])
        return response.Response(MemberSerializer(member, context={"request": request}).data)


class MemberConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


@contextmanager
def _domain_errors(conflict=False, field=None):
    """Traduce la `ValidationError` de Django de los servicios a la de DRF.

    Sin esto una regla de negocio incumplida llegaria al cliente como un 500.
    """
    try:
        yield
    except DjangoValidationError as exc:
        if conflict:
            raise MemberConflict(" ".join(exc.messages)) from exc
        if hasattr(exc, "error_dict"):
            raise ValidationError(exc.message_dict) from exc
        raise ValidationError({field: exc.messages} if field else exc.messages) from exc


def _photo_response(member):
    """Foto privada de una ficha ya autorizada: nunca se guarda en caches compartidas."""
    if not member.photo:
        return response.Response(status=404)
    from django.http import FileResponse

    photo = FileResponse(member.photo.open("rb"), content_type="image/webp")
    photo["Cache-Control"] = "private, no-store"
    return photo


class MemberMeView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _member(self, request):
        association_id = request.headers.get("X-Association-ID") or request.query_params.get("association_id") or request.data.get("association")
        require_roles(request.user, association_id, {AssociationRole.Role.MEMBER, *MANAGER_ROLES})
        try:
            return Member.objects.prefetch_related("member_instruments__instrument").get(association_id=association_id, account=request.user)
        except Member.DoesNotExist as exc:
            raise ValidationError(_("No hay una ficha vinculada a esta cuenta.")) from exc

    def get(self, request):
        member = self._member(request)
        return response.Response(MemberSerializer(member, context={"request": request, "own_profile": True}).data)

    def patch(self, request):
        member = self._member(request)
        for field in ("email", "phone", "address"):
            if field in request.data:
                setattr(member, field, request.data[field])
        member.save(update_fields=["email", "phone", "address", "updated_at"])
        return response.Response(MemberSerializer(member, context={"request": request, "own_profile": True}).data)


def _money(value):
    return f"{value:.2f}"


def _utc(moment):
    """RFC 3339 en UTC terminado en `Z`, como fija el contrato."""
    return moment.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z") if moment else None


class MemberEarningsView(MemberMeView):
    """Lo que se adeuda y se ha pagado a la ficha propia (decision 0011).

    Sin paginar: lo acota el numero de actividades remuneradas de una persona.
    Nunca devuelve importes de otras fichas.
    """

    http_method_names = ["get", "head", "options"]

    def get(self, request):
        member = self._member(request)
        summary = member_earnings(member)
        return response.Response(
            {
                "currency": "EUR",
                "owed_total": _money(summary.owed_total),
                "paid_total": _money(summary.paid_total),
                "items": [
                    {
                        "invitation": str(item.invitation.pk),
                        "activity": {
                            "id": str(item.invitation.activity.pk),
                            "title": item.invitation.activity.title,
                            "starts_at": _utc(item.invitation.activity.starts_at),
                        },
                        "amount": _money(item.amount),
                        "status": item.status,
                        "paid_at": _utc(item.payment.paid_at) if item.payment else None,
                    }
                    for item in summary.items
                ],
            }
        )

class MemberMePhotoView(MemberMeView):
    def get(self, request):
        """Descarga la foto de la ficha propia (rol member o gestor con ficha vinculada)."""
        return _photo_response(self._member(request))

    def put(self, request):
        member = self._member(request)
        if "photo" not in request.FILES:
            raise ValidationError({"photo": _("Adjunta una imagen.")})
        with _domain_errors(field="photo"):
            member = member_services.replace_member_photo(member=member, actor=request.user, upload=request.FILES["photo"])
        return response.Response(MemberSerializer(member, context={"request": request, "own_profile": True}).data)

    def delete(self, request):
        member = self._member(request)
        member_services.delete_member_photo(member=member, actor=request.user)
        return response.Response(status=204)


class SectionViewSet(ScopedViewSet):
    serializer_class = SectionSerializer
    ordering = ("order", "name", "id")

    def get_queryset(self):
        self.check_access()
        return Section.objects.filter(association_id=self.association_id())

    def perform_create(self, serializer):
        self.check_access(manager=True)
        serializer.save(association_id=self.association_id())


class InstrumentViewSet(ScopedViewSet):
    serializer_class = InstrumentSerializer
    ordering = ("name", "id")

    def get_queryset(self):
        self.check_access()
        return Instrument.objects.filter(association_id=self.association_id()).select_related("section")

    def perform_create(self, serializer):
        self.check_access(manager=True)
        serializer.save(association_id=self.association_id())


class TransportViewSet(ScopedViewSet):
    serializer_class = TransportSerializer
    ordering = ("id",)

    def get_queryset(self):
        access = self.check_access()
        queryset = Transport.objects.filter(activity__association_id=self.association_id())
        roles = set(access.role_assignments.values_list("role", flat=True))
        if not self.request.user.is_superuser and not roles.intersection(MANAGER_ROLES):
            queryset = queryset.filter(assignments__member__account=self.request.user)
        return queryset.select_related("activity", "driver").distinct()

    def perform_create(self, serializer):
        self.check_access(manager=True)
        activity = Activity.objects.get(pk=serializer.validated_data["activity"].pk, association_id=self.association_id())
        serializer.save(activity=activity)


class TransportAssignmentViewSet(ScopedViewSet):
    serializer_class = TransportAssignmentSerializer
    ordering = ("id",)

    def get_queryset(self):
        access = self.check_access()
        queryset = TransportAssignment.objects.filter(transport__activity__association_id=self.association_id())
        roles = set(access.role_assignments.values_list("role", flat=True))
        if not self.request.user.is_superuser and not roles.intersection(MANAGER_ROLES):
            queryset = queryset.filter(member__account=self.request.user)
        return queryset.select_related("transport", "transport__activity", "member")

    def _save_assignment(self, serializer):
        current = serializer.instance
        requested_transport = serializer.validated_data.get(
            "transport", current.transport if current else None
        )
        requested_member = serializer.validated_data.get(
            "member", current.member if current else None
        )
        transport = Transport.objects.select_for_update().get(
            pk=requested_transport.pk,
            activity__association_id=self.association_id(),
        )
        member = Member.objects.get(
            pk=requested_member.pk,
            association_id=self.association_id(),
        )
        other_assignments = TransportAssignment.objects.filter(
            member=member,
            transport__activity=transport.activity,
        )
        occupied_seats = transport.assignments.all()
        if current:
            other_assignments = other_assignments.exclude(pk=current.pk)
            occupied_seats = occupied_seats.exclude(pk=current.pk)
        if other_assignments.exists():
            raise ValidationError({"member": _("El miembro ya tiene transporte para esta actividad.")})
        if occupied_seats.count() >= transport.capacity:
            raise ValidationError({"transport": _("No quedan plazas disponibles.")})
        serializer.save(transport=transport, member=member)

    @transaction.atomic
    def perform_create(self, serializer):
        self.check_access(manager=True)
        self._save_assignment(serializer)

    @transaction.atomic
    def perform_update(self, serializer):
        self.check_access(manager=True)
        self._save_assignment(serializer)


class ActivityViewSet(ScopedViewSet):
    serializer_class = ActivitySerializer
    ordering = ("starts_at", "id")

    def association_id(self):
        value = self.request.headers.get("X-Association-ID") or self.request.query_params.get("association_id") or self.request.data.get("association")
        if value:
            return value
        activity_id = self.kwargs.get("pk")
        if activity_id:
            return Activity.objects.only("association_id").get(pk=activity_id).association_id
        return super().association_id()

    def get_queryset(self):
        association_id = self.association_id()
        self.check_access()
        queryset = Activity.objects.filter(association_id=association_id)
        access = AssociationAccess.objects.filter(account=self.request.user, association_id=association_id, is_active=True).first()
        roles = set(access.role_assignments.values_list("role", flat=True)) if access else set()
        if not self.request.user.is_superuser and not roles.intersection(MANAGER_ROLES):
            queryset = queryset.filter(status=Activity.Status.PUBLISHED, invitations__member__account=self.request.user).distinct()
        return queryset.prefetch_related("programme", "invitations__member", "invitations__attendance")

    def perform_create(self, serializer):
        self.check_access(manager=True)
        serializer.save()

    def perform_update(self, serializer):
        self.check_access(manager=True)
        serializer.save()

    @decorators.action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        self.check_access(manager=True)
        from apps.activities.services import publish_activity

        result = publish_activity(self.get_object(), request.user)
        return response.Response(self.get_serializer(result["activity"]).data)

    @decorators.action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self.check_access(manager=True)
        from apps.activities.services import cancel_activity

        result = cancel_activity(self.get_object(), request.user, reason=request.data.get("reason", ""))
        return response.Response(self.get_serializer(result["activity"]).data)

    @decorators.action(detail=True, methods=["post"])
    def invite(self, request, pk=None):
        self.check_access(manager=True)
        activity = self.get_object()
        members = Member.objects.filter(association_id=activity.association_id)
        if not request.data.get("all_active_musicians", False):
            members = members.filter(id__in=request.data.get("member_ids", []))
        from apps.activities.services import invitation_notice, invite_members, notify_activity

        result = invite_members(activity, members, mandatory=request.data.get("is_mandatory"))
        activity = result["activity"]
        if activity.status == Activity.Status.PUBLISHED:
            notify_activity(activity, "invitation", invitation_notice(activity))
        return response.Response(
            {"invited": result["eligible"], "created": result["created"], "existing": result["existing"]}
        )

    @decorators.action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        invitation = Invitation.objects.select_related("activity", "member").get(pk=request.data.get("invitation_id"), activity_id=pk)
        updated = respond(invitation, request.user, request.data.get("response"), request.data.get("note", ""))
        return response.Response(InvitationSerializer(updated).data)

    @decorators.action(detail=True, methods=["post"], url_path="attendance/(?P<invitation_id>[^/.]+)")
    def attendance(self, request, pk=None, invitation_id=None):
        self.check_access(manager=True)
        # La convocatoria debe ser de esta actividad y de la asociacion comprobada:
        # sin el filtro, un gestor de otra banda podia pasar lista aqui.
        invitation = get_object_or_404(
            Invitation, pk=invitation_id, activity_id=pk, activity__association_id=self.association_id()
        )
        result = record_attendance(invitation, request.user, request.data.get("status"), request.data.get("note", ""))
        return response.Response({"status": result.status, "note": result.note})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    ordering = ("-created_at", "-id")

    def get_queryset(self):
        return Notification.objects.filter(account=self.request.user).select_related("activity", "poll")

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.read_at = timezone.now()
        obj.save(update_fields=["read_at"])
        return response.Response(self.get_serializer(obj).data)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.data.get("is_read") is True:
            obj.read_at = timezone.now()
            obj.save(update_fields=["read_at"])
        return response.Response(self.get_serializer(obj).data)


class ImportPreviewView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        association_id = request.data.get("association_id")
        require_roles(request.user, association_id, {AssociationRole.Role.ADMIN})
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": _("Adjunta un CSV o XLSX.")})
        mapping = request.data.get("mapping", {})
        if isinstance(mapping, str):
            import json

            mapping = json.loads(mapping)
        association = Association.objects.get(pk=association_id)  # require_roles ya comprobó el acceso
        _content, content_hash, preview = parse_import(upload, mapping, association=association)
        batch = ImportBatch.objects.filter(
            association_id=association_id,
            content_hash=content_hash,
        ).first()
        response_status = status.HTTP_200_OK
        if not batch:
            batch = ImportBatch(
                association_id=association_id,
                created_by=request.user,
                filename=upload.name,
                content_hash=content_hash,
            )
            response_status = status.HTTP_201_CREATED
        if batch.status != ImportBatch.Status.CONFIRMED:
            batch.mapping = mapping
            batch.source_headers = list(mapping)
            batch.preview = preview
            batch.status = ImportBatch.Status.PREVIEW
            batch.save()
        return response.Response(
            {
                "id": batch.id,
                "status": batch.status,
                "preview": batch.preview,
                "result": batch.result,
                "rows": len(batch.preview),
            },
            status=response_status,
        )


class ImportConfirmView(APIView):
    def post(self, request, pk):
        batch = get_object_or_404(ImportBatch, pk=pk)
        require_roles(request.user, batch.association_id, {AssociationRole.Role.ADMIN})
        return response.Response(confirm_import(batch))
