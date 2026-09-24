# Instrucciones de prueba del MVP

Estado a 24 de septiembre de 2026. Complementa a [README.md](README.md) (cómo
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

Los 403 de `platform` y `web_editor` son intencionados: operan la plataforma o el
complemento web y no participan en la banda. Desde el 23/09/2026 la lista de
permisos de `/auth/me` ya no les promete lo contrario.

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

1. ~~**`DJANGO_DEBUG` no hace efecto en Docker.**~~ Resuelto el 23/09/2026: ver
   el apartado 4.
2. ~~**Incoherencia de permisos en `platform` y `web_editor`.**~~ Resuelto el
   23/09/2026: ver el apartado 4 y
   [docs/decisions/0002-alcance-de-lectura-por-rol.md](docs/decisions/0002-alcance-de-lectura-por-rol.md).

3. **Repertorio solo al crear.** El panel fija el repertorio al crear la actividad;
   para cambiarlo después hay que usar la API o el Django Admin.
4. **Push de encuestas en Flutter.** La app Flutter abre una encuesta desde su
   lista, no desde una notificación push: el envío FCM todavía no existe en el
   backend y el aviso solo lleva `activity_id` en los datos push.
5. **Listas de la app web.** Encuestas, agenda y avisos leen solo la primera
   página (50 elementos); no siguen `next`.

## 4. Cambios del 24/09/2026

### Qué probar con cada cuenta

| Cuenta | Dónde | Qué hacer |
| --- | --- | --- |
| `prova-board` o `prova-admin` | Panel, `http://localhost:8080/panel/` | «Mi acceso»: roles y lo que puedes y no puedes hacer. «Nueva actividad»: crear un ensayo o una actuación con repertorio. En el detalle, publicar y convocar a todos o a una selección por cuerdas, instrumentos o personas. «Encuestas»: crear, elegir destinatarios, abrir, ver el provisional, publicar tras el plazo, anular. |
| `prova-member` | App del músico, `http://localhost:8080/app/` | Pestaña «Encuestas»: votar con confirmación, ver «Has votado» y el provisional. Los avisos de encuesta y de convocatoria abren su detalle. |
| `prova-member` | Panel | 403, con enlace a «Mi acceso». |

Para ver el paso «pendiente de publicar» sin esperar al plazo, crea una encuesta con
un cierre a pocos minutos vista.

### Encuestas

Implementadas según ANALISIS.md 3.7: servidor, API `/api/v1/polls/`, panel de la
junta, app web del músico y cliente Flutter. El voto único y el anonimato se
garantizan en el servidor. Las cuatro decisiones que quedaban abiertas y los
límites del anonimato están en
[docs/decisions/0007-encuestas-con-voto-unico-y-anonimo.md](docs/decisions/0007-encuestas-con-voto-unico-y-anonimo.md).
Cubierto por `backend/tests/test_polls.py`, `backend/tests/test_panel_polls.py`,
`backend/tests/test_member_app.py` y `mobile/test/polls_test.dart`.

### Panel: crear actividades, convocar por selección y «Mi acceso»

Hasta ahora una actividad solo se podía crear por la API o el Django Admin, y solo
se podía convocar a todos los músicos activos. El panel permite ya crearla y
convocar por cuerdas, instrumentos o personas. «Mi acceso» (`/panel/me/`) enseña
los roles y una tabla de capacidades calculada con la misma función que usa
`/api/v1/auth/me` (`permissions_for` en `backend/apps/associations/permissions.py`).
Cubierto por `backend/tests/test_panel_activities.py`.

### Error CSRF al entrar en la app con la sesión del panel abierta

Con la cookie del panel en el navegador, `POST /api/v1/auth/login` pasaba por
`SessionAuthentication`, que exige CSRF. El acceso y la renovación ya no autentican
por sesión. Cubierto por `LoginWithPanelSessionTests`.

### Datos de prueba en un PC nuevo

La base de datos vive en un volumen de Docker de cada máquina: en un PC nuevo
empieza vacía y las cuentas de prueba no existen. Para recrearlas:

```bash
docker compose --env-file infra/.env -f infra/compose.yaml exec web python manage.py shell -c \
  "from apps.associations.models import Association; Association.objects.get_or_create(slug='AUMB', defaults={'name': 'AUMB Bocairent'})"
docker compose --env-file infra/.env -f infra/compose.yaml exec web \
    python manage.py seed_role_accounts --association AUMB --force
```

El censo real de 30 fichas no está en este repositorio. Las cuerdas (Metal,
Madera, Percusión) y los instrumentos de las fichas DEMO del PC secundario se
añadieron a mano para probar la convocatoria por selección.

## 5. Correcciones aplicadas el 23/09/2026

### Lectura de las variables booleanas de entorno

`backend/config/settings.py` leia los cuatro interruptores comparando con la
cadena exacta `"1"`, mientras que `infra/.env` y `infra/compose.yaml` escriben
`true`. El efecto era que `DJANGO_DEBUG`, `CELERY_TASK_ALWAYS_EAGER`,
`FCM_ENABLED` y `DJANGO_SECURE_COOKIES` se quedaban en falso en silencio; el
entorno Docker de desarrollo corria con DEBUG desactivado y la siembra exigia
`--force`.

Ahora un ayudante `env_flag` acepta `1/true/yes/on` y `0/false/no/off` sin
distinguir mayusculas ni espacios, trata el valor vacio como ausente y detiene el
arranque con `ImproperlyConfigured` ante un valor no reconocido, para que una
errata no vuelva a leerse como falso. Cubierto por `backend/tests/test_settings.py`.

### Permisos anunciados a `platform` y `web_editor`

`/api/v1/auth/me` anunciaba `activities.view` a cualquier acceso activo, tambien
a `platform` y `web_editor`, y despues `ScopedViewSet.check_access` les respondia
403. `notifications.view` no formaba parte del problema: ese extremo filtra por
cuenta, no por asociacion, asi que el anuncio ya era cierto.

Se decidio rebajar el anuncio en vez de conceder la lectura, por lo razonado en
[docs/decisions/0002-alcance-de-lectura-por-rol.md](docs/decisions/0002-alcance-de-lectura-por-rol.md).
El conjunto `PARTICIPANT_ROLES` de `backend/apps/associations/permissions.py` es
ahora la unica definicion que leen el anuncio y la comprobacion, de modo que no
puedan volver a separarse. Cubierto por `backend/tests/test_role_permissions.py`,
que recorre los siete roles.

### Aviso al modificar, publicar o cancelar una actividad

Una actividad publicada se podia editar sin que nadie se enterara, y no habia
forma de cancelarla avisando. Ahora:

- Cambiar titulo, inicio, final, concentracion, lugar, uniforme, plazo o
  asistencia obligatoria avisa a quien esta convocado.
- Cambiar inicio, concentracion o lugar ademas devuelve las respuestas a
  pendiente y pide reconfirmar; la respuesta anulada queda en el historial.
- El estado deja de ser escribible con `PATCH`. Se cambia con `publish` o con
  `cancel`, que avisan; cancelar exige un motivo, como pedia el contrato.
- Publicar avisa a quien se convoco mientras la actividad era borrador.
- El panel de la junta incorpora el formulario de cambio y el de cancelacion, y
  advierte si el plazo de respuesta ya vencio cuando se anulan las respuestas.

Razonamiento en
[docs/decisions/0003-aviso-de-cambios-en-actividades.md](docs/decisions/0003-aviso-de-cambios-en-actividades.md).
Cubierto por `backend/tests/test_activity_changes.py`, que recorre API, panel y
los tres idiomas.

### Los avisos por correo no salian

`deliver_email_task` estaba definida y no la invocaba nadie: las entregas de
correo se quedaban en `pending` indefinidamente. `queue_notification_deliveries`
las encola ahora al confirmar la transaccion, y solo las pendientes.

### Catalogos de traduccion

Las cadenas nuevas estan traducidas a valenciano e ingles. Al regenerar los
catalogos, `msgmerge` habia propuesto conjeturas *fuzzy* equivocadas —
`Concentración` como «Administració de Gesband»—; no llegaban a compilarse, pero
se han vaciado para que los catalogos digan lo que es cierto.

## 6. Correcciones aplicadas el 22/09/2026

En `backend/tests/test_mvp.py`, que impedían ejecutar la suite completa:

- El import de `mail` venía de `django.contrib` en vez de `django.core`, lo que
  rompía la carga del módulo y dejaba los 21 tests sin ejecutar.
- `test_member_cannot_manage_access_invitations` arrastraba un bloque copiado de
  otro test con nombres inexistentes (`detail_url`, `activity`). Sustituido por
  una comprobación real: que el músico tampoco pueda hacer POST al panel de
  accesos.

Resultado: `python manage.py test tests` pasa los 21 tests.
