# Manual de administración de la plataforma (`platform`)

Para quien opera el servicio Gesband: da de alta asociaciones, asigna los primeros
administradores y da soporte. **No participa en la vida de la banda.**

## Qué concede el rol, y qué no

El rol `platform` dentro de una asociación **no da acceso a sus datos**. Es a
propósito, para que operar el servicio no suponga leer el censo de cada banda
([decisión 0002](../decisions/0002-alcance-de-lectura-por-rol.md)):

| Pantalla | Resultado |
| --- | --- |
| Panel de la junta, censo, actividades, encuestas | «Sin permiso» (403) |
| API `/members/`, `/activities/` | 403 |
| «Mi acceso» (`/panel/me/`) | Muestra tus roles |
| Avisos y dispositivos propios | Sí |

Hoy el trabajo de operación se hace desde la **administración interna** (Django
Admin, `/admin/`). Para entrar en ella hace falta una cuenta de personal (`is_staff`),
que se concede aparte del rol. Úsala solo para operar y con el mínimo acceso
necesario.

## Tareas habituales

**Dar de alta una asociación.** En la administración interna → Asociaciones: nombre,
identificador corto (`slug`), zona horaria (`Europe/Madrid`), logo, colores y lema.

**Asignar el primer administrador de la banda.**

1. Crea la cuenta (Cuentas) con usuario, correo y contraseña provisional, y comunícala
   por un canal seguro. La persona entra con su correo.
2. Crea su acceso a la asociación y añádele el rol `admin`. A partir de ahí, la propia
   banda importa el censo e invita a los músicos.

**Asignar roles de junta.** Añade `board`, `organizer` o `director` al acceso de la
persona. Los roles se acumulan: un músico de la junta tiene `member` y `board`.

**Restablecer una contraseña.** Desde la ficha de la cuenta en la administración
interna. Todavía no hay recuperación de contraseña por correo.

**Editar el repertorio de una actividad ya creada.** Desde la administración interna.
El panel todavía no lo permite.

**Cargar transporte.** Desde la administración interna o la API mientras no haya
pantallas en el panel. El servidor controla las plazas y los duplicados.

**Revisar los envíos de avisos.** En «Entregas de avisos» se ve cada envío por canal
(push o correo), su estado, los intentos y el último error. En «Dispositivos
registrados» y «Pruebas de avisos» se ve el estado de MUST-NOTIF-01 de cada instalación:
permiso, token vigente y última recepción confirmada. El token push no se muestra.

## Entorno y datos de prueba

- Levantar el entorno y sembrar las cuentas por rol: [README.md](../../README.md) e
  [INSTRUCCIONES.md](../../INSTRUCCIONES.md).
- Push reales a dispositivos de prueba: [infra/secrets/README.md](../../infra/secrets/README.md).
  Con `PUSH_PROVIDER=fake`, el valor por omisión, no sale nada de la máquina.
- En pruebas, nunca uses datos ni destinatarios reales.

## Precauciones

- Un superusuario no sirve para comprobar permisos: el servidor le deja pasar siempre.
  Para ver lo que ve una junta, usa las cuentas de prueba por rol.
- No copies DNI, tokens ni contraseñas en tickets, logs o mensajes.
- No publiques una foto privada de un músico en ningún sitio.
- No despliegues a producción ni envíes comunicaciones reales sin autorización expresa.

## Todavía no se puede

- Operar la plataforma con un panel propio: se usa la administración interna.
- Registrar una auditoría de los accesos administrativos excepcionales.
