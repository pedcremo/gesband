# Credenciales locales

Esta carpeta se monta en solo lectura en `/run/gesband-secrets` dentro de `web` y
`worker`. Git ignora todo su contenido salvo este fichero.

Para enviar push reales a dispositivos de prueba:

1. En la consola de Firebase del proyecto de pruebas, *Configuración del proyecto →
   Cuentas de servicio → Generar nueva clave privada*.
2. Guarda el JSON como `infra/secrets/firebase-service-account.json`. El usuario
   `app` del contenedor tiene otro uid: el fichero debe ser legible para él
   (`chmod 444`), así que protege la carpeta y la máquina, no solo el fichero.
3. En `infra/.env`: `PUSH_PROVIDER=fcm` y
   `FCM_CREDENTIALS_FILE=/run/gesband-secrets/firebase-service-account.json`.
4. `docker compose --env-file infra/.env -f infra/compose.yaml up -d web worker`.

Solo con dispositivos y cuentas de prueba autorizados: con `fcm` los avisos salen de
verdad.
