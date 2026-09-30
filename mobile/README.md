# App móvil de Gesband

Cliente Flutter para Android e iOS del MVP. Identificadores de la app:

| Plataforma | Identificador | Configuración |
| --- | --- | --- |
| Android | `applicationId = "es.gesband.app"` | `android/app/build.gradle.kts` |
| iOS | `PRODUCT_BUNDLE_IDENTIFIER = es.gesband.app` | `ios/Runner.xcodeproj` |

SDK usado: Flutter 3.47.5 (Dart 3.13). Si la terminal no lo encuentra:
`export PATH=/home/pedcremo/.local/share/flutter/bin:$PATH`.

## Comprobaciones

```bash
cd mobile
flutter pub get --enforce-lockfile
flutter analyze --fatal-infos --fatal-warnings
flutter test
flutter build apk --debug          # funciona sin google-services.json
```

`flutter build ios` solo funciona en macOS con Xcode.

## Configuración de Firebase (no se versiona)

La app usa Firebase Cloud Messaging en Android y FCM sobre APNs en iOS. Los
ficheros de configuración contienen identificadores del proyecto de Firebase y
están en `.gitignore`; cada persona los coloca en su copia:

| Fichero | Ruta |
| --- | --- |
| `google-services.json` | `mobile/android/app/google-services.json` |
| `GoogleService-Info.plist` | `mobile/ios/Runner/GoogleService-Info.plist` |

1. En la consola de Firebase, usar un proyecto **de pruebas** (nunca el de
   producción para probar) y registrar dos apps con el identificador
   `es.gesband.app`: una Android y otra iOS.
2. Descargar los dos ficheros y copiarlos en las rutas anteriores.
3. iOS: en *Configuración del proyecto → Cloud Messaging → Configuración de la
   app de Apple*, subir la clave APNs (`.p8`) del equipo de Apple
   Developer. Sin ella FCM acepta el mensaje pero no llega al iPhone.
4. El backend de pruebas necesita la cuenta de servicio de ese mismo proyecto y
   `PUSH_PROVIDER=fcm`: ver [infra/secrets/README.md](../infra/secrets/README.md).
   Con el valor por omisión, `fake`, no sale ningún aviso hacia los móviles.

Sin estos ficheros la app compila y arranca: `Firebase.initializeApp()` falla
de forma controlada, el paso de avisos muestra «no disponibles» y se puede
continuar. En Android, Gradle avisa `google-services.json no existe` y no
aplica el plugin `com.google.gms.google-services`. En iOS, la fase de
compilación *Copy Firebase config* copia el plist al paquete solo si existe.

## Android

- `minSdk` es el mayor entre el de Flutter y 23; `firebase_messaging` exige 21.
- El manifiesto declara `POST_NOTIFICATIONS` (Android 13+ pide permiso en
  tiempo de ejecución) e `INTERNET`.
- Canal por defecto `gesband_default` («Avisos de la banda»), declarado en el
  meta-data `com.google.firebase.messaging.default_notification_channel_id` y
  creado en `MainActivity` al abrir la app. El nombre se traduce en
  `res/values*/strings.xml`.
- Solo la variante de depuración permite HTTP en claro, para probar contra
  `http://10.0.2.2:8000` (emulador) o la IP del portátil en la wifi. Perfil y
  publicación exigen HTTPS.

Ejecutar en un móvil conectado por USB, contra el servidor de pruebas:

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8000/api/v1
```

## iOS (en macOS)

Ya está preparado en el repositorio:

- `ios/Runner/Runner.entitlements` con `aps-environment = development`,
  referenciado en `CODE_SIGN_ENTITLEMENTS` de Debug, Release y Profile.
- `UIBackgroundModes` con `remote-notification` en `Info.plist`.
- `NSAllowsLocalNetworking` para probar por HTTP contra un servidor de la red
  local; los servidores desplegados deben usar HTTPS.

Pasos manuales en Xcode (`open ios/Runner.xcworkspace`):

1. *Runner → Signing & Capabilities*: elegir el equipo (Team) de Apple
   Developer. Con firma automática, Xcode crea el perfil con la capacidad
   Push Notifications.
2. Comprobar que aparecen las capacidades **Push Notifications** y **Background
   Modes → Remote notifications**. Si Xcode no reconoce el entitlements ya
   referenciado, añadirlas con «+ Capability»: el resultado es el mismo
   fichero.
3. Copiar `GoogleService-Info.plist` en `ios/Runner/` (no hace falta añadirlo al
   proyecto: lo copia la fase *Copy Firebase config*).
4. `flutter run --dart-define=API_BASE_URL=...` con el iPhone conectado. El
   simulador no sirve para validar la recepción push de MUST-NOTIF-01.

Al archivar para TestFlight, Xcode sustituye `aps-environment` por
`production` según el perfil de distribución.

## Contrato de notificaciones

La app sigue `contracts/openapi.yaml` (etiqueta *Devices*):

| Momento | Llamada |
| --- | --- |
| Primera sesión en la instalación | `POST /devices` con `installation_id` (UUID v4 guardado), `platform`, `push_token`, `permission_state`, `app_version`, `locale` |
| Arranque, vuelta a la app (p. ej. desde ajustes), cambio de idioma | `PATCH /devices/{id}` con el permiso observado; el token solo si cambió |
| Rotación del token | `PATCH /devices/{id}` con `push_token` |
| Tras cada sincronización | `GET /devices/{id}/notification-capability` decide el paso visible |
| Prueba de recepción | `POST /devices/{id}/push-tests` con `expected_presentation` |
| Llega la prueba | `POST /push-tests/{id}/confirm` con `received_foreground` u `opened_from_background` y `occurred_at` en UTC con `Z` |
| Cierre de sesión | `DELETE /devices/{id}`, después `deleteToken()` y borrado del id local |

- `permission_state` es el estado real del sistema. Android no distingue
  «sin preguntar» de «denegado»: antes de la primera solicitud desde la app se
  envía `not_determined`; después, `denied`, y la pantalla ofrece abrir ajustes
  en lugar de repetir una solicitud que el sistema ya no muestra.
- El token se registra aunque el permiso esté denegado o sea provisional; el
  servidor decide la acción. Tener token no se presenta como avisos activos.
- Las pruebas recibidas en segundo plano o sin sesión se guardan (solo el id
  opaco de la prueba) y se confirman al abrir la app o iniciar sesión. Si falla
  la red, se reintentan al volver a la app con la misma `Idempotency-Key`.
- Avisos normales: `kind` (`activity`, `poll`, `notification`),
  `notification_id`, `activity_id`, `poll_id`. Al pulsarlos se abre la
  actividad o la encuesta; en primer plano aparece un aviso en la parte
  inferior con «Abrir» y la agenda se recarga.
- Idioma enviado: `es` → `es-ES`, `ca` → `ca-ES-valencia`, `en` → `en`.
- La app no escribe tokens ni el contenido de los avisos en logs.

## Guion de prueba manual MUST-NOTIF-01

Hacerlo en **un Android 13+ y un iPhone reales**, con el backend de pruebas y
un proveedor push de pruebas, y con cuentas sintéticas (nunca personas reales).
Anotar para cada paso: dispositivo, versión del sistema, resultado y hora.
Preparar dos cuentas de prueba (A y B), cada una con una actividad y una
encuesta abierta en la misma banda.

1. **Instalación limpia y permiso concedido.** Desinstalar la app, instalarla,
   entrar con A y elegir banda. El paso de avisos muestra *Permiso: sin
   solicitar*. Pulsar «Activar notificaciones» y aceptar en el diálogo del
   sistema. Esperado: *Permiso: concedido*, *Dispositivo registrado: sí*,
   *Recepción comprobada: pendiente*.
2. **Prueba en primer plano.** Pulsar «Enviar aviso de prueba» sin salir de la
   app. Esperado: aparece «Aviso de prueba recibido», *Última prueba: recibida
   con la app abierta* y *Recepción comprobada: sí*. En el backend, la prueba
   pasa a `received_foreground`.
3. **Prueba en segundo plano.** Pulsar «Probar con la app en segundo plano»,
   volver al escritorio, esperar el aviso del sistema y pulsarlo. Esperado: la
   app se abre y la prueba pasa a `opened_from_background`. Repetir con la app
   cerrada del todo (deslizarla fuera de recientes).
4. **Permiso denegado.** Desinstalar e instalar de nuevo, entrar y denegar el
   diálogo. Android 13 puede mostrarlo una segunda vez; iOS no. Esperado: la
   app deja de ofrecer la solicitud y muestra «Abrir ajustes del sistema» con
   la explicación de la consecuencia; *Dispositivo registrado* puede ser *sí*
   (el token se registra), pero *Permiso* sigue *denegado*. Se puede pulsar
   «Ahora no» y la agenda muestra el aviso «Los avisos no están completamente
   activados» con «Revisar».
5. **Reactivación desde ajustes.** Desde ese estado, «Abrir ajustes del
   sistema», activar las notificaciones de Gesband y volver a la app. Esperado:
   sin reiniciar, *Permiso: concedido* y el siguiente paso es la prueba.
6. **Revocación desde ajustes.** Con todo activado, ir a los ajustes del
   sistema, desactivar las notificaciones de Gesband y volver. Esperado:
   aparece «Se han desactivado las notificaciones de Gesband…» con acceso a
   ajustes, el banner de la agenda vuelve a mostrarse y en el backend el
   dispositivo consta con `permission_state = denied`.
7. **Canal de Android.** En *Ajustes → Apps → Gesband → Notificaciones* existe
   el canal «Avisos de la banda» y los avisos llegan por él (no por «Varios»).
8. **Token renovado.** El sistema decide cuándo rota el token y no se puede
   forzar desde fuera. Para comprobar que un token nuevo sustituye al anterior:
   cerrar sesión con A y volver a entrar con A. `deleteToken()` invalida el
   token anterior; al entrar, el backend recibe `POST /devices` con la misma
   `installation_id` (respuesta 200, instalación existente) y el token nuevo.
   Esperado: una prueba nueva llega y un envío al token anterior falla en el
   proveedor. La rotación espontánea (`onTokenRefresh` → `PATCH` con
   `push_token`) está cubierta por pruebas unitarias; si ocurre durante el
   piloto, debe verse como `PATCH /devices/{id}` en el backend (el token nunca
   aparece en logs).
9. **Aviso de actividad.** Desde el panel, cambiar el horario de la actividad
   de A. Con la app en primer plano: aparece el aviso inferior con «Abrir», que
   abre esa actividad, y la agenda se recarga. Con la app en segundo plano o
   cerrada: pulsar el aviso del sistema abre esa misma actividad (tras
   completar el paso de avisos si se estaba en él).
10. **Aviso de encuesta.** Abrir una encuesta para A desde el panel. Pulsar el
    aviso abre el detalle de esa encuesta, no la agenda.
11. **Cambio de cuenta.** Con A activado, cerrar sesión. Esperado: el backend
    registra `DELETE /devices/{id}` y el dispositivo queda revocado. Enviar un
    aviso a A: no debe llegar a este móvil. Entrar con B: se registra un
    dispositivo nuevo para B, la prueba llega y un aviso para A sigue sin
    llegar; uno para B sí.
12. **Sin Firebase.** Compilar sin `google-services.json` /
    `GoogleService-Info.plist`: la app arranca, el paso de avisos dice que no
    están disponibles y se puede continuar hasta la agenda.

Riesgos que hay que mirar expresamente en iOS: la plantilla de Flutter 3.47
usa el ciclo de vida de escenas (`SceneDelegate`). Comprobar en los pasos 3 y 9
que el aviso pulsado con la app **cerrada** abre la pantalla correcta; si no,
es un problema de `firebase_messaging` con escenas y hay que registrarlo.
