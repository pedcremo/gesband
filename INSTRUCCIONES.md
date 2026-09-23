# Instrucciones de prueba del MVP

Estado a 22 de septiembre de 2026. Complementa a [README.md](README.md) (cómo
levantar el entorno) y a [AGENTS.md](AGENTS.md) (reglas de trabajo).

## 1. Cuentas de prueba por rol

Sembradas en la asociación **AUMB Bocairent** (slug `AUMB`). Ninguna es
superusuaria: por eso ejercitan de verdad las comprobaciones de rol del servidor.

Contraseña común: `Gesband.demo.2026`

| Rol | Correo (móvil y API) | Usuario (panel web) |
| --- | --- | --- |
| `member` | prova-member@gesband.invalid | prova-member |
| `board` | prova-board@gesband.invalid | prova-board |
| `organizer` | prova-organizer@gesband.invalid | prova-organizer |
| `director` | prova-director@gesband.invalid | prova-director |
| `admin` | prova-admin@gesband.invalid | prova-admin |
| `platform` | prova-platform@gesband.invalid | prova-platform |
| `web_editor` | prova-web_editor@gesband.invalid | prova-web_editor |

El dominio `.invalid` está reservado por la IANA: ninguna de estas direcciones
puede corresponder a una persona real ni recibir correo.

Cada cuenta tiene una ficha de miembro vinculada (`external_id` con prefijo
`DEMO-`) y está convocada a las actividades publicadas futuras, de modo que el
recorrido del músico se puede recorrer entero desde la app.

### Dónde entra cada una

- Panel de la junta: `http://localhost:8080/accounts/login/` con el **usuario**.
- API y app móvil: `POST /api/v1/auth/login` con el **correo** y la contraseña.

### Qué ve cada rol (verificado el 22/09/2026)

| Rol | Panel junta | `GET /members/` | `GET /activities/` |
| --- | --- | --- | --- |
| `member` | 403 | 403 | 200 (solo su convocatoria) |
| `board` | 200 | 200 | 200 |
| `organizer` | 200 | 200 | 200 |
| `director` | 200 | 200 | 200 |
| `admin` | 200 | 200 | 200 (además importación y ajustes) |
| `platform` | 403 | 403 | 403 |
| `web_editor` | 403 | 403 | 403 |

El músico ve en la agenda **solo su propia convocatoria**, no las de los demás.

> **`pedcremo` no sirve para probar permisos.** Es superusuario: `require_roles`
> lo deja pasar siempre (`backend/apps/associations/permissions.py:27`) y la API
> le devuelve `["*"]` en la lista de permisos. Para observar lo que ve una junta
> o una administración reales, usa `prova-board` y `prova-admin`.

## 2. Cómo volver a sembrarlas

El comando es idempotente: repetirlo no duplica cuentas, accesos, fichas ni
convocatorias.

```bash
# Sobre el entorno Docker
docker compose --env-file infra/.env -f infra/compose.yaml exec web \
    python manage.py seed_role_accounts --force

# En local
.venv/bin/python backend/manage.py seed_role_accounts --association AUMB
```

Opciones: `--password` y `--reset-password` para fijar la contraseña,
`--no-invite` para no añadir convocatorias a las actividades existentes,
`--domain` (solo acepta TLD reservados) y `--force` para ejecutarlo con `DEBUG`
desactivado.

El código está en
`backend/apps/associations/management/commands/seed_role_accounts.py`.

### Efecto sobre los datos existentes

La siembra añadió 7 fichas sintéticas al censo (de 30 a 37) y 7 convocatorias al
ensayo del 25 (de 30 a 37). Se distinguen por el `external_id` `DEMO-*` y se
pueden borrar sin tocar el censo real.

## 3. Puntos abiertos detectados

Ninguno introducido por la siembra; son del código anterior.

1. **`DJANGO_DEBUG` no hace efecto en Docker.** `infra/.env` define
   `DJANGO_DEBUG=true`, pero `backend/config/settings.py:8` solo activa DEBUG con
   el valor exacto `"1"`. El entorno de desarrollo corre con DEBUG desactivado.
   Sin decidir: corregir la lectura del valor o ajustar el `.env`. Mientras tanto,
   los comandos de siembra necesitan `--force` en ese entorno.
2. **Incoherencia de permisos en `platform` y `web_editor`.** `/api/v1/auth/me`
   les anuncia `activities.view` y `notifications.view`, pero
   `ScopedViewSet.check_access` (`backend/apps/api.py:261`) les responde 403
   porque no son ni `member` ni rol de gestión. Decisión de producto pendiente: o
   el serializador promete de más, o esos roles deberían implicar lectura de
   miembro.

## 4. Correcciones aplicadas el 22/09/2026

En `backend/tests/test_mvp.py`, que impedían ejecutar la suite completa:

- El import de `mail` venía de `django.contrib` en vez de `django.core`, lo que
  rompía la carga del módulo y dejaba los 21 tests sin ejecutar.
- `test_member_cannot_manage_access_invitations` arrastraba un bloque copiado de
  otro test con nombres inexistentes (`detail_url`, `activity`). Sustituido por
  una comprobación real: que el músico tampoco pueda hacer POST al panel de
  accesos.

Resultado: `python manage.py test tests` pasa los 21 tests.
