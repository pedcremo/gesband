"""Cliente web del musico.

Es una herramienta de desarrollo para recorrer el producto desde el papel del
musico sin compilar la app movil: habla con `/api/v1/` igual que ella, desde el
mismo origen, y no comparte la sesion del panel de la junta. No sustituye al
cliente Flutter ni es el complemento web de la asociacion de ANALISIS.md.
"""

from hashlib import blake2s
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import render
from django.views.decorators.cache import never_cache

# Lo que el service worker guarda para funcionar sin conexion.
SHELL_FILES = ("member_app/app.css", "member_app/app.js", "member_app/icon.svg")

_version_cache = None


def shell_version():
    """Huella del cascaron.

    El service worker solo se reinstala si su propio texto cambia, y los ficheros
    estaticos no llevan hash en el nombre. Sin esta huella, quien ya tenga la app
    instalada se queda con la version vieja para siempre.
    """
    global _version_cache
    if _version_cache and not settings.DEBUG:
        return _version_cache

    digest = blake2s(digest_size=8)
    for name in SHELL_FILES:
        found = finders.find(name)
        if found:
            digest.update(Path(found).read_bytes())
    _version_cache = digest.hexdigest()
    return _version_cache


@never_cache
def member_app(request):
    """Carcasa de la aplicacion. La sesion vive en el token, no en la cookie."""
    return render(request, "member_app/index.html", {"shell_version": shell_version()})


@never_cache
def member_app_service_worker(request):
    """Se sirve desde /app/ para que su alcance sea esa ruta y no /static/."""
    return render(
        request,
        "member_app/service-worker.js",
        {"shell_version": shell_version()},
        content_type="application/javascript",
    )


@never_cache
def member_app_manifest(request):
    return render(
        request,
        "member_app/manifest.webmanifest",
        content_type="application/manifest+json",
    )
