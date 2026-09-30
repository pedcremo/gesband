"""Dispositivos y pruebas de recepcion (MUST-NOTIF-01).

Todo se filtra por la cuenta autenticada: una instalacion ajena devuelve 404,
igual que una inexistente. Los tokens push se aceptan pero nunca se devuelven.
"""

from django.shortcuts import get_object_or_404
from rest_framework import response, serializers, status
from rest_framework.views import APIView

from . import services
from .models import DeviceRegistration, PushTest

LOCALES = ["es-ES", "ca-ES-valencia", "en"]


class DeviceRegistrationSerializer(serializers.ModelSerializer):
    permission_state = serializers.CharField(source="permission", read_only=True)
    token_registered = serializers.BooleanField(read_only=True)
    active = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = DeviceRegistration
        fields = [
            "id",
            "installation_id",
            "platform",
            "permission_state",
            "token_registered",
            "active",
            "app_version",
            "locale",
            "last_seen_at",
            "revoked_at",
        ]
        read_only_fields = fields


class DeviceRegistrationInputSerializer(serializers.Serializer):
    installation_id = serializers.UUIDField()
    platform = serializers.ChoiceField(choices=DeviceRegistration.Platform.choices)
    push_token = serializers.CharField(min_length=20, max_length=4096, write_only=True)
    permission_state = serializers.ChoiceField(choices=DeviceRegistration.Permission.choices)
    app_version = serializers.CharField(max_length=50, allow_blank=True)
    locale = serializers.ChoiceField(choices=LOCALES, required=False, allow_blank=True, default="")


class DeviceRegistrationUpdateSerializer(serializers.Serializer):
    push_token = serializers.CharField(min_length=20, max_length=4096, write_only=True, required=False)
    permission_state = serializers.ChoiceField(choices=DeviceRegistration.Permission.choices, required=False)
    app_version = serializers.CharField(max_length=50, allow_blank=True, required=False)
    locale = serializers.ChoiceField(choices=LOCALES, required=False, allow_blank=True)


class NotificationCapabilitySerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    permission_state = serializers.CharField()
    token_registered = serializers.BooleanField()
    receipt_confirmed = serializers.BooleanField()
    last_receipt_confirmed_at = serializers.DateTimeField(allow_null=True)
    action_required = serializers.CharField()
    checked_at = serializers.DateTimeField()


class PushTestSerializer(serializers.ModelSerializer):
    device_id = serializers.UUIDField(read_only=True)
    provider_error_code = serializers.SerializerMethodField()

    class Meta:
        model = PushTest
        fields = [
            "id",
            "device_id",
            "expected_presentation",
            "status",
            "provider_error_code",
            "created_at",
            "expires_at",
            "confirmed_at",
        ]
        read_only_fields = fields

    def get_provider_error_code(self, obj):
        return obj.provider_error_code or None


class PushTestInputSerializer(serializers.Serializer):
    expected_presentation = serializers.ChoiceField(choices=PushTest.Presentation.choices)


class PushTestConfirmSerializer(serializers.Serializer):
    event = serializers.ChoiceField(
        choices=[PushTest.Status.RECEIVED_FOREGROUND, PushTest.Status.OPENED_FROM_BACKGROUND]
    )
    occurred_at = serializers.DateTimeField()


def _conflict(exc):
    return response.Response({"code": exc.code, "detail": exc.message}, status=status.HTTP_409_CONFLICT)


def _own_device(request, device_id):
    return get_object_or_404(DeviceRegistration, pk=device_id, account=request.user, is_active=True)


def _own_push_test(request, push_test_id):
    return get_object_or_404(PushTest.objects.select_related("device"), pk=push_test_id, account=request.user)


class DeviceListView(APIView):
    def get(self, request):
        devices = DeviceRegistration.objects.filter(account=request.user, is_active=True).order_by("-last_seen_at")
        return response.Response({"results": DeviceRegistrationSerializer(devices, many=True).data})

    def post(self, request):
        data = DeviceRegistrationInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        device, created = services.register_device(
            account=request.user,
            installation_id=values["installation_id"],
            platform=values["platform"],
            push_token=values["push_token"],
            permission=values["permission_state"],
            app_version=values["app_version"],
            locale=values["locale"],
        )
        return response.Response(
            DeviceRegistrationSerializer(device).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DeviceDetailView(APIView):
    def patch(self, request, device_id):
        device = _own_device(request, device_id)
        data = DeviceRegistrationUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        services.update_device(
            device,
            push_token=values.get("push_token"),
            permission=values.get("permission_state"),
            app_version=values.get("app_version"),
            locale=values.get("locale"),
        )
        return response.Response(DeviceRegistrationSerializer(device).data)

    def delete(self, request, device_id):
        device = DeviceRegistration.objects.filter(pk=device_id, account=request.user).first()
        if device:
            services.revoke_device(device)
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class NotificationCapabilityView(APIView):
    def get(self, request, device_id):
        capability = services.notification_capability(_own_device(request, device_id))
        return response.Response(NotificationCapabilitySerializer(capability).data)


class DevicePushTestView(APIView):
    def post(self, request, device_id):
        device = _own_device(request, device_id)
        data = PushTestInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            test = services.request_push_test(
                device, account=request.user, expected_presentation=data.validated_data["expected_presentation"]
            )
        except services.PushTestConflict as exc:
            return _conflict(exc)
        test.refresh_from_db()
        return response.Response(PushTestSerializer(test).data, status=status.HTTP_202_ACCEPTED)


class PushTestDetailView(APIView):
    def get(self, request, push_test_id):
        test = services.expire_if_due(_own_push_test(request, push_test_id))
        return response.Response(PushTestSerializer(test).data)


class PushTestConfirmView(APIView):
    def post(self, request, push_test_id):
        test = _own_push_test(request, push_test_id)
        data = PushTestConfirmSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            test = services.confirm_push_test(test, **data.validated_data)
        except services.PushTestConflict as exc:
            return _conflict(exc)
        return response.Response(PushTestSerializer(test).data)
