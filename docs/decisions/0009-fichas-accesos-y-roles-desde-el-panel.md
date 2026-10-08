# Fichas, accesos y roles desde el panel

Fecha: 8 de octubre de 2026.

## Contexto

Hasta ahora el panel de la junta solo permitía consultar el censo. Nadie podía dar de
alta, editar o dar de baja una ficha desde el panel, ni gestionar su foto. Las
invitaciones de acceso eran solo de `admin` y los roles los asignaba el operador de la
plataforma desde la administración interna.

La API sí dejaba a cualquier rol de gestión crear, editar y **borrar físicamente**
fichas, sin comprobar si tenían historial. Un error de foto no válida por la API
respondía con un 500.

El promotor decidió el 8 de octubre de 2026 quién puede hacer qué.

## Decisión

**Fichas del censo.** `admin`, `board`, `organizer` y `director` (`MANAGER_ROLES`,
permiso `members.manage`) pueden desde el panel y la API:

- Dar de alta una ficha y editar sus datos, tipo, estado, instrumentos (la cuerda es la
  del instrumento) y cargos registrables.
- Subir, sustituir y eliminar su foto, con la validación existente
  (`apps/members/images.py`): contenido real, 5 MB, píxeles, sin metadatos y nombre
  interno aleatorio. La foto se sirve por una vista autorizada con
  `Cache-Control: private, no-store`, nunca desde una ruta pública.
- Dar de baja (estado `inactive`) y reactivar. La baja es lógica: no borra
  convocatorias, respuestas, asistencia, encuestas ni transporte. Una ficha inactiva no
  se convoca ni se invita.

**Borrado físico.** Solo `admin` (permiso nuevo `members.delete`), con una página de
confirmación. Regla elegida, la más segura: se borra **únicamente** una ficha que no ha
dejado rastro, es decir, sin convocatorias (y por tanto sin asistencia), sin haber sido
destinataria de encuestas, sin transporte asignado ni como conductora, y sin una cuenta
de acceso vinculada. En cualquier otro caso el servidor lo impide (409 en la API) y
explica que se use la baja. Las claves `PROTECT` de esas tablas ya lo garantizaban en la
base de datos; el servicio lo comprueba antes y da un motivo comprensible. El caso típico
es corregir una ficha creada por error.

**Accesos y roles.** `admin` y `board` (permisos nuevos `accounts.manage` y
`roles.manage`) pueden invitar, reenviar y revocar invitaciones, conceder y quitar roles
y desactivar o reactivar el acceso de una cuenta a su asociación. Reglas del servidor:

- El rol `admin` solo lo concede o lo quita otro `admin`. Por coherencia, solo un `admin`
  puede desactivar o reactivar el acceso de una cuenta que tenga `admin`.
- `platform` y `web_editor` no se conceden ni se quitan desde el panel: siguen siendo
  del operador de la plataforma.
- Ninguna operación puede dejar la asociación sin un `admin` activo (acceso activo y
  cuenta activa). Se bloquean las filas de los administradores para que dos cambios
  simultáneos no lo consigan.
- Nadie desactiva su propio acceso.
- No se borran cuentas: la identidad es global y puede pertenecer a otras asociaciones.
  Desactivar un acceso afecta solo a esta asociación.

`organizer` y `director` gestionan fichas, no accesos ni roles. La importación del censo
sigue siendo solo de `admin`.

**Dónde viven las reglas.** En servicios reutilizados por el panel y la API:
`apps/members/services.py` (`create_member`, `update_member`, `set_member_status`,
`delete_member`, `replace_member_photo`, `delete_member_photo`) y
`apps/accounts/services.py` (`grant_role`, `revoke_role`, `set_access_active` y las
comprobaciones añadidas a `issue_access_invitation` y `revoke_access_invitation`). Cada
servicio comprueba el permiso con `ensure_permission`, que lee `permissions_for`, la
misma fuente que anuncian `/api/v1/auth/me` y «Mi acceso». Las entidades relacionadas
(instrumentos, accesos) se comprueban dentro de la asociación: una de otra asociación se
rechaza o responde 404.

**Trazabilidad.** No existía un sistema de auditoría general y no se crea uno:

- La ficha guarda `created_by`, `updated_by`, `status_changed_at` y `status_changed_by`.
- Los cambios de rol y de acceso quedan en `AccessChange` (acción, rol, quién, cuándo),
  porque `AssociationRole` no tiene fechas ni autor y su modelo pertenece a otro
  propietario. El panel muestra los últimos cambios.
- Las invitaciones ya guardaban `created_by` y `revoked_by`.
- Un borrado físico deja una línea de log con los identificadores de la ficha y de la
  cuenta, sin datos personales.

**Cargos registrables.** Nuevo modelo `MemberPosition` con presidencia,
vicepresidencia, secretaría, tesorería, contratista y vocalía. Son informativos y no
conceden permisos, como establece `ANALISIS.md`. Se añade secretaría, que no figuraba en
la lista del análisis, porque es un cargo habitual de la junta de una asociación.

## Consecuencias

- Cambio de comportamiento expreso: por la API, `DELETE /api/v1/members/{id}` pasa de
  estar abierto a todos los roles de gestión a ser solo de `admin`, y responde 409 si la
  ficha tiene historial. El contrato lo documenta.
- La foto no válida por la API responde ahora 400 con el error en `photo`.
- Las pruebas `backend/tests/test_member_management.py`,
  `backend/tests/test_access_management.py` y las nuevas de
  `backend/tests/test_role_permissions.py` recorren la matriz de los siete roles, una
  cuenta en dos asociaciones, la escalada de privilegios y el último `admin`.
- Desactivar el acceso de una cuenta no revoca sus tokens ni sus dispositivos: siguen
  sirviendo para sus otras asociaciones, y el servidor ya rechaza cada operación sobre
  la asociación desactivada. Tampoco se ha cambiado el envío de avisos: quien ya estaba
  convocado a una actividad sigue recibiendo sus cambios aunque su ficha pase a baja o su
  acceso se desactive. Si eso molesta en el piloto, se filtrará en `communications`.
- Pendiente: no hay todavía extremos REST para gestionar accesos y roles; si la app los
  necesita, se añadirán sobre los mismos servicios. Tampoco hay gestión de cuerdas ni
  instrumentos desde el panel.
