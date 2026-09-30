# Envío push y prueba de recepción (MUST-NOTIF-01)

Fecha: 30 de septiembre de 2026.

## Contexto

MUST-NOTIF-01 exige comprobar por separado el permiso, el registro del dispositivo y
una prueba de recepción. El servidor creaba entregas push para cada aviso, pero no
las enviaba nadie: no había emisor FCM. `POST /devices/test` devolvía un
`challenge_id` inventado sin mandar nada. La app confirmaba la prueba en una ruta que
no existía. `contracts/openapi.yaml` ya describía el recorrido correcto
(`notification-capability`, `push-tests`, `confirm`), pero ni el servidor ni la app
lo seguían.

## Decisión

- **Un adaptador por proveedor** (`apps/communications/push.py`), elegido con
  `PUSH_PROVIDER`. `fake`, el valor por omisión, guarda los mensajes en memoria y no
  sale de la máquina. `fcm` usa `firebase-admin` con una cuenta de servicio montada
  fuera de Git (`infra/secrets/`). FCM también entrega en iOS a través de APNs, así que
  no hay un segundo adaptador.
- **Los errores del proveedor se clasifican.** Un token rechazado
  (`unregistered`, `sender-id-mismatch`, `invalid-argument`) marca el dispositivo con
  `token_invalidated_at` y no se reintenta. Hasta que la app registre otro token,
  `notification-capability` pide `register_token`. La falta de disponibilidad o la
  cuota se reintentan hasta cinco veces con espera creciente. En el último intento, la
  entrega queda en `failed` con un código saneado que nunca incluye el token.
- **La recepción solo vale para el token vigente.** `receipt_confirmed` exige una
  prueba confirmada posterior a `token_updated_at`. Tener permiso y token no se
  presenta nunca como recepción demostrada.
- **Un permiso provisional no es un permiso pleno.** Aunque se confirme la prueba,
  el siguiente paso propuesto sigue siendo `request_system_permission`.
- **Un teléfono pertenece a una sola cuenta.** Registrar una instalación o un token
  desde otra cuenta borra el vínculo anterior. Antes de cada envío se vuelve a
  comprobar que el dispositivo sigue siendo de la cuenta del aviso. Así, tras un
  cambio de sesión, no llega a una persona un aviso de otra.
- **El mensaje solo lleva identificadores**: `kind`, `notification_id`,
  `association_id`, `activity_id` o `poll_id` y `deep_link`. El título y el cuerpo son
  los del aviso de la bandeja. La prueba usa un texto fijo en el idioma de la
  instalación.
- **La prueba caduca** a los `PUSH_TEST_TTL_MINUTES` (10 por omisión). Confirmarla dos
  veces, en primer plano y al abrirla, conserva el primer evento.

## Consecuencias

- Las pruebas del servidor (`backend/tests/test_push.py`) usan siempre el proveedor
  falso. Enviar a un dispositivo real requiere activar `fcm` a mano y con un
  dispositivo de prueba autorizado.
- Nada de esto demuestra MUST-NOTIF-01. El requisito exige verificarlo en Android e
  iOS reales, con el guion de `mobile/README.md`.
- No se promete entrega exactamente una vez. Una entrega `sent` no se reenvía, pero
  FCM puede duplicar o perder mensajes sin avisar.
- Las respuestas de error 409 usan `{code, detail}`, como el resto de la API
  actual, y no `application/problem+json`. `Idempotency-Key` sigue sin implementarse
  en ninguna ruta. Ambas divergencias con el contrato son anteriores y globales.
