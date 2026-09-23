# Alcance de lectura por rol: `platform` y `web_editor` no leen datos de la banda

Fecha: 23 de septiembre de 2026.

## Contexto

`AssociationSerializer.get_permissions` anunciaba `activities.view` a cualquier
cuenta con acceso activo a una asociación, sin mirar sus roles. La comprobación
del servidor, en cambio, exigía ser `member` o rol de gestión.

Las dos cuentas que caen fuera de esa lista quedaban con una promesa incumplida:
la API les decía que podían leer actividades y después les respondía 403.

- `platform` («Administración de plataforma») opera Gesband, no participa en la
  banda.
- `web_editor` («Edición web») corresponde al complemento web, que `AGENTS.md`
  mantiene documentado pero sin construir.

Había dos salidas posibles: rebajar el anuncio, o conceder lectura a esos dos
roles.

## Decisión

Rebajar el anuncio. El conjunto `PARTICIPANT_ROLES` vive en
`backend/apps/associations/permissions.py` junto a `MANAGER_ROLES`, y lo leen
tanto el serializador que anuncia permisos como `ScopedViewSet.check_access`, de
modo que anuncio y comprobación no puedan separarse otra vez.

Conceder la lectura habría ampliado el alcance de datos personales a dos roles
que no asisten a ensayos ni salidas, en contra de la regla de dominio de que los
datos privados pertenecen a la asociación, y habría dado por construido el
complemento web.

`notifications.view`, `devices.manage_own` y `association.view` siguen en el
conjunto base de cualquier acceso activo: sus extremos filtran por cuenta o por
acceso, no por rol, así que el anuncio ya era cierto para ellos.

## Consecuencias

`platform` y `web_editor` mantienen acceso a la asociación y a sus propias
notificaciones y dispositivos, y ninguna lectura del censo ni de la agenda.
Cuando el complemento web entre en alcance, `web_editor` necesitará su propio
permiso explícito; no lo hereda por estar dentro de la asociación.

`backend/tests/test_role_permissions.py` recorre los siete roles y comprueba, rol
a rol, que lo anunciado coincide con lo que la API concede.
