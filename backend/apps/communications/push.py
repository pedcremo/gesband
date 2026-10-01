"""Adaptadores de envio push.

`PUSH_PROVIDER=fake` (por omision) no sale de la maquina: guarda los mensajes en
`FakePushProvider.outbox` para pruebas y desarrollo. `PUSH_PROVIDER=fcm` usa
Firebase Cloud Messaging, que tambien entrega en iOS a traves de APNs.

Ningun error devuelto al resto del sistema incluye el token: solo un codigo
saneado.
"""

import logging
import threading
import uuid
from dataclasses import dataclass, field

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

ANDROID_CHANNEL_ID = "gesband_default"


@dataclass(frozen=True)
class PushMessage:
    token: str
    title: str
    body: str
    data: dict = field(default_factory=dict)


class PushError(Exception):
    """Fallo del proveedor. `code` es un identificador corto y sin datos privados."""

    permanent = False

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class TemporaryPushError(PushError):
    """El proveedor no esta disponible o limita el ritmo: se puede reintentar."""


class InvalidTokenError(PushError):
    """El token ya no sirve; hay que esperar a que la app registre otro."""

    permanent = True


class RejectedPushError(PushError):
    """El proveedor rechaza el mensaje por algo que no cambia al reintentar."""

    permanent = True


class FakePushProvider:
    outbox = []
    # Codigos que el siguiente envio debe simular, en orden: permite probar fallos.
    scripted_failures = []
    _lock = threading.Lock()

    def send(self, message):
        with self._lock:
            if self.scripted_failures:
                raise self.scripted_failures.pop(0)
            self.outbox.append(message)
        return f"fake-{uuid.uuid4()}"

    @classmethod
    def reset(cls):
        with cls._lock:
            cls.outbox.clear()
            cls.scripted_failures.clear()


class FcmPushProvider:
    _app = None
    _lock = threading.Lock()

    def _firebase_app(self):
        import firebase_admin
        from firebase_admin import credentials

        with self._lock:
            if FcmPushProvider._app is None:
                path = settings.FCM_CREDENTIALS_FILE
                if not path:
                    raise ImproperlyConfigured("PUSH_PROVIDER=fcm necesita FCM_CREDENTIALS_FILE.")
                FcmPushProvider._app = firebase_admin.initialize_app(
                    credentials.Certificate(path), name="gesband-push"
                )
            return FcmPushProvider._app

    def send(self, message):
        from firebase_admin import exceptions, messaging
        from google.auth import exceptions as auth_exceptions

        fcm_message = messaging.Message(
            token=message.token,
            notification=messaging.Notification(title=message.title, body=message.body),
            data={key: str(value) for key, value in message.data.items() if value is not None},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(channel_id=ANDROID_CHANNEL_ID),
            ),
            apns=messaging.APNSConfig(payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))),
        )
        try:
            return messaging.send(fcm_message, app=self._firebase_app())
        except (messaging.UnregisteredError, messaging.SenderIdMismatchError) as exc:
            raise InvalidTokenError(_code(exc)) from None
        except (messaging.QuotaExceededError, exceptions.UnavailableError, exceptions.InternalError,
                exceptions.DeadlineExceededError) as exc:
            raise TemporaryPushError(_code(exc)) from None
        except exceptions.InvalidArgumentError as exc:
            # FCM responde asi tanto a un token mal formado como a un mensaje
            # invalido; el mensaje lo construimos nosotros, asi que es el token.
            raise InvalidTokenError(_code(exc)) from None
        except exceptions.FirebaseError as exc:
            raise RejectedPushError(_code(exc)) from None
        except auth_exceptions.RefreshError:
            # Google rechaza la cuenta de servicio: es configuracion, no red.
            logger.error("FCM rechaza las credenciales de la cuenta de servicio")
            raise RejectedPushError("credentials_rejected") from None
        except Exception as exc:
            # Sin DNS, sin red o cualquier fallo imprevisto antes de llegar a FCM
            # (p. ej. `google.auth.exceptions.TransportError`): se reintenta en vez
            # de dejar la entrega o la prueba en cola para siempre. No se registra
            # el mensaje, que podria llevar el token.
            logger.warning("Fallo de conexion con FCM: %s", type(exc).__name__)
            raise TemporaryPushError(type(exc).__name__.lower()[:64]) from None


def _code(exc):
    return str(getattr(exc, "code", "") or type(exc).__name__).lower()[:64]


PROVIDERS = {"fake": FakePushProvider, "fcm": FcmPushProvider}


def get_push_provider():
    try:
        return PROVIDERS[settings.PUSH_PROVIDER]()
    except KeyError:
        raise ImproperlyConfigured(
            f"PUSH_PROVIDER debe ser uno de {sorted(PROVIDERS)}, no {settings.PUSH_PROVIDER!r}."
        ) from None
