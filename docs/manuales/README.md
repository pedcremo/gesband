# Manuales de uso de Gesband

Estado a 30 de septiembre de 2026. Describen lo que el MVP permite hacer hoy, no lo
previsto en [ANALISIS.md](../../ANALISIS.md). Cada manual indica al final qué
**todavía no** se puede hacer desde su rol.

| Rol | Manual | Para quién |
| --- | --- | --- |
| `member` — Músico | [musico.md](musico.md) | Cada músico de la banda. |
| `board` — Junta | [junta.md](junta.md) | Presidencia, vicepresidencia, secretaría, vocalías. |
| `organizer` — Contratista/organización | [organizacion.md](organizacion.md) | Quien prepara actuaciones y salidas. |
| `director` — Dirección musical | [direccion-musical.md](direccion-musical.md) | Director o directora de la banda. |
| `admin` — Administración | [administracion.md](administracion.md) | Quien mantiene el censo y los accesos de la asociación. |
| `platform` — Administración de plataforma | [administracion-plataforma.md](administracion-plataforma.md) | Operación del servicio Gesband. |
| `web_editor` — Edición web | [edicion-web.md](edicion-web.md) | Complemento web futuro. |

## Conceptos comunes

**Roles y cargos no son lo mismo.** El cargo (presidencia, tesorería…) es una
etiqueta. Lo que puedes hacer depende del rol. Una persona puede acumular varios
roles, por ejemplo `member` y `board`, y entonces usa los dos manuales.

**Una cuenta, varias bandas.** Si tu cuenta pertenece a más de una asociación, eliges
la banda al entrar. Tus roles, y los datos que ves, son distintos en cada una.

**Ficha y cuenta son distintas.** La ficha es tu registro en el censo de la banda. La
cuenta es tu acceso. Puede haber fichas sin cuenta: socios colaboradores o músicos que
no usan la app.

**Dónde se entra:**

| Herramienta | Dirección (entorno de pruebas) | Con qué |
| --- | --- | --- |
| Panel de la junta | `http://localhost:8080/panel/` | Correo (o usuario) y contraseña |
| App móvil (Android/iOS) | Se instala en el móvil | Correo y contraseña |
| App web del músico (pruebas) | `http://localhost:8080/app/` | Correo y contraseña |
| Mi acceso | `http://localhost:8080/panel/me/` | Cualquier rol con acceso |

**«Mi acceso»** muestra tus roles y una tabla de lo que puedes y no puedes hacer.
El servidor calcula esa tabla con la misma regla que aplica a cada operación: es la
referencia fiable si un manual y la realidad no coinciden.

**Idiomas.** Panel y apps están en castellano, valenciano e inglés. En el panel se
cambia con el selector «Idioma», en la cabecera.

**Cuentas de prueba.** Hay una cuenta sintética por rol en
[INSTRUCCIONES.md](../../INSTRUCCIONES.md), con la contraseña común. Úsalas para
seguir estos manuales sin datos reales.

## Limitaciones que afectan a todos los roles

- **No hay recuperación de contraseña.** Si alguien la olvida, la debe restablecer el
  operador de la plataforma.
- **Los roles de gestión los asigna el operador de la plataforma** desde la
  administración interna. Una invitación de acceso solo concede el rol `member`.
