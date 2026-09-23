"""Cliente web del musico.

Es una herramienta de desarrollo para recorrer el producto desde el papel del
musico sin compilar la app movil: habla con `/api/v1/` igual que ella, desde el
mismo origen, y no comparte la sesion del panel de la junta. No sustituye al
cliente Flutter ni es el complemento web de la asociacion de ANALISIS.md.
"""

from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
def member_app(request):
    """Carcasa de la aplicacion. La sesion vive en el token, no en la cookie."""
    return render(request, "member_app/index.html")


@never_cache
def member_app_service_worker(request):
    """Se sirve desde /app/ para que su alcance sea esa ruta y no /static/."""
    return render(
        request,
        "member_app/service-worker.js",
        content_type="application/javascript",
    )


@never_cache
def member_app_manifest(request):
    return render(
        request,
        "member_app/manifest.webmanifest",
        content_type="application/manifest+json",
    )
