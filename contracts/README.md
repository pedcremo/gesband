# Contrato HTTP del MVP de Gesband

`openapi.yaml` es la fuente de verdad del contrato entre el backend, la app móvil y
el panel web para la API `/api/v1/`. Describe OpenAPI 3.1 y usa exclusivamente datos
sintéticos.

## Convenciones cerradas

- Los identificadores son UUID opacos. El cliente no extrae información de ellos.
- Las fechas y horas de la API son RFC 3339 en UTC y terminan en `Z`. La asociación
  declara su zona IANA para presentarlas, inicialmente `Europe/Madrid`.
- Toda ruta con datos de una asociación exige `X-Association-ID`. El servidor obtiene
  la cuenta del token, comprueba su pertenencia y filtra todas las entidades por esa
  asociación. El encabezado no concede acceso por sí mismo.
- Las colecciones usan cursor (`page[cursor]`, `page[size]`) y devuelven `next_cursor`.
- Los fallos usan `application/problem+json`, con un `code` estable y errores de campo
  opcionales. `trace_id` sirve para soporte y no contiene datos privados.
- Las creaciones y acciones que pueden repetirse aceptan `Idempotency-Key`. Una misma
  clave, cuenta, asociación y operación conserva el primer resultado; reutilizarla con
  otro cuerpo devuelve `409`.
- `ETag`/`If-Match` protegen las ediciones en las que perder una actualización sería
  relevante. Un valor obsoleto devuelve `412`.
- La autenticación móvil usa pares de tokens de acceso y renovación revocables. El
  contrato no prescribe una implementación criptográfica propia.

## Permisos resumidos

Los roles son acumulables y están separados de los cargos descriptivos. Las operaciones
declaran su permiso en `x-permissions`. Los permisos del MVP son:

| Permiso | Uso |
| --- | --- |
| `association.view` | Consultar la asociación activa. |
| `association.manage` | Editar identidad visual y configuración. |
| `members.view` / `members.manage` | Consultar o mantener el censo. |
| `members.private_data.view` | Ver datos personales restringidos. |
| `members.photo.view` / `members.photo.manage` | Descargar o cambiar fotos privadas. |
| `imports.manage` | Preparar y confirmar importaciones. |
| `activities.view` / `activities.manage` | Consultar o mantener actividades. |
| `invitations.manage` | Previsualizar y emitir convocatorias. |
| `attendance.manage` | Registrar asistencia real. |
| `transport.view` / `transport.manage` | Consultar o asignar transporte. |
| `notifications.view` | Consultar la bandeja de avisos propia. |
| `devices.manage_own` | Gestionar los dispositivos de la sesión propia. |

El backend puede dar a una persona acceso solamente a sus propios datos aunque no tenga
un permiso de grupo. Las respuestas nunca amplían visibilidad por compartir cuenta entre
dos asociaciones.

## Notificaciones y MUST-NOTIF-01

`notification-capability` informa por separado del permiso observado por la app, el
registro vigente del dispositivo y la última prueba confirmada. El backend no interpreta
un token como permiso concedido ni como recepción demostrada. La app vuelve a enviar el
estado al iniciar, regresar de ajustes y cuando cambie el token.

`push-tests` crea una prueba dirigida al dispositivo autenticado. La recepción se confirma
con el identificador opaco incluido en el mensaje, tanto en primer plano como al abrirlo.
La confirmación prueba ese envío concreto, no garantiza entregas futuras. Los tokens push
nunca aparecen en respuestas de lectura ni en avisos.

## Validación

Desde la raíz del repositorio, si está disponible `npx`:

```bash
npx --yes @redocly/cli lint contracts/openapi.yaml
```

Como comprobación sin descargar dependencias, cualquier analizador YAML 1.2 puede cargar
el fichero. La validación semántica debe realizarse en CI con una versión fijada de
Redocly cuando se prepare la infraestructura. No se incluye ahora un archivo de bloqueo
global porque pertenece al integrador.

Antes de fusionar cambios del backend se comparará su esquema generado con este contrato.
Los cambios incompatibles requieren una nueva versión de API o una decisión explícita.

