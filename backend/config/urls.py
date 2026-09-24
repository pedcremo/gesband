from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView

from config.member_app import member_app, member_app_manifest, member_app_service_worker
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.polls.api import PollViewSet
from apps.accounts.views import activate_invitation, activation_complete
from apps.api import (
    ActivityViewSet,
    AssociationViewSet,
    DeviceReceiptView,
    DeviceTestView,
    DeviceView,
    ImportConfirmView,
    ImportPreviewView,
    LoginView,
    RefreshView,
    LogoutView,
    MemberViewSet,
    MemberMeView,
    MemberMePhotoView,
    MeView,
    NotificationViewSet,
    SectionViewSet,
    InstrumentViewSet,
    TransportViewSet,
    TransportAssignmentViewSet,
)
from config.panel import (
    activity_create,
    activity_detail,
    dashboard,
    my_access,
    member_import_detail,
    member_import_start,
    member_import_template,
    member_access_invitations,
    members,
)

router = DefaultRouter()
router.register("associations", AssociationViewSet, basename="association")
router.register("members", MemberViewSet, basename="member")
router.register("activities", ActivityViewSet, basename="activity")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("sections", SectionViewSet, basename="section")
router.register("instruments", InstrumentViewSet, basename="instrument")
router.register("transports", TransportViewSet, basename="transport")
router.register("polls", PollViewSet, basename="poll")
router.register("transport-assignments", TransportAssignmentViewSet, basename="transport-assignment")

urlpatterns = [
    # La raiz lleva al panel; si no hay sesion, `login_required` pasa por el acceso.
    path("", RedirectView.as_view(pattern_name="panel", permanent=False), name="home"),
    path("health/", lambda request: JsonResponse({"status": "ok"}), name="health"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/activate/<str:token>/", activate_invitation, name="account-invitation-activate"),
    path("accounts/activation-complete/", activation_complete, name="account-activation-complete"),
    path("app/", member_app, name="member-app"),
    path("app/sw.js", member_app_service_worker, name="member-app-service-worker"),
    path("app/manifest.webmanifest", member_app_manifest, name="member-app-manifest"),
    path("panel/", dashboard, name="panel"),
    path("panel/members/", members, name="panel-members"),
    path("panel/members/access/", member_access_invitations, name="member-access-invitations"),
    path("panel/members/import/", member_import_start, name="member-import-start"),
    path("panel/members/import/template.csv", member_import_template, name="member-import-template"),
    path("panel/members/import/<uuid:batch_id>/", member_import_detail, name="member-import-detail"),
    path("panel/me/", my_access, name="panel-my-access"),
    path("panel/activities/new/", activity_create, name="activity-create"),
    path("panel/activities/<uuid:activity_id>/", activity_detail, name="activity-detail"),
    path("api/v1/auth/login", LoginView.as_view(), name="api-login"),
    path("api/v1/auth/refresh", RefreshView.as_view(), name="api-refresh"),
    path("api/v1/auth/logout", LogoutView.as_view(), name="api-logout"),
    path("api/v1/auth/me", MeView.as_view(), name="api-me"),
    path("api/v1/devices", DeviceView.as_view(), name="api-devices"),
    path("api/v1/devices/receipt", DeviceReceiptView.as_view(), name="api-device-receipt"),
    path("api/v1/devices/test", DeviceTestView.as_view(), name="api-device-test"),
    path("api/v1/members/me/", MemberMeView.as_view(), name="api-member-me"),
    path("api/v1/members/me/photo/", MemberMePhotoView.as_view(), name="api-member-me-photo"),
    path("api/v1/imports/preview", ImportPreviewView.as_view(), name="api-import-preview"),
    path("api/v1/imports/<uuid:pk>/confirm", ImportConfirmView.as_view(), name="api-import-confirm"),
    path("api/v1/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
