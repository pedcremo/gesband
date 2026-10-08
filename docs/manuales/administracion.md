# Manual de administración de la asociación (`admin`)

Para cargar y mantener el censo, invitar a los músicos a usar la app, repartir los
roles y configurar la asociación. Además, `admin` puede hacer todo lo de la junta:
actividades, convocatorias, asistencia, encuestas, fichas del censo y accesos, descritos
en [junta.md](junta.md).

Lo que solo puede hacer `admin`:

| Tarea | Dónde |
| --- | --- |
| Importar miembros desde CSV o XLSX | «Miembros» → «Importar miembros» |
| Borrar definitivamente una ficha sin historial | Ficha → «Borrar esta ficha…» |
| Conceder o quitar el rol `admin` | «Miembros» → «Accesos y roles» |
| Cambiar el nombre o la zona horaria de la asociación | Mediante el operador de la plataforma (ver al final) |

Invitar a los músicos, conceder los demás roles, activar o desactivar accesos y
cambiar la imagen de la banda (logo, colores, lema, estilo y modo, en «Imagen de la
banda»; ver [junta.md](junta.md#11-imagen-de-la-banda)) lo comparte con `board`. Dar de alta, editar y dar de baja fichas lo comparte con `board`,
`organizer` y `director`.

## 1. Importar el censo

**Preparar el fichero**

1. «Miembros» → «Importar miembros» → «Descargar plantilla CSV». La plantilla trae
   una fila de ejemplo. En la columna de tipo se escribe `musician` (músico socio),
   `supporter` (socio colaborador o mecenas) o `external` (colaborador musical
   externo).
2. Columnas admitidas: identificador externo (número de socio), nombre, apellidos
   (juntos, o primer y segundo apellido por separado), DNI/NIE, dirección, teléfono,
   correo electrónico y tipo de miembro. Solo el nombre y los apellidos son
   obligatorios.
3. Límites: CSV en UTF-8 o XLSX, hasta 5 MB y 1 000 filas. No se ejecutan fórmulas ni
   macros. No se descargan fotos desde URLs de la hoja.

**Usar un identificador externo estable.** Es lo que permite repetir la importación
para actualizar fichas sin duplicarlas. Gesband **no** fusiona personas por nombre,
correo o teléfono: dos hermanos pueden compartir correo.

**Importar**

1. En «Fichero CSV o XLSX», sube el fichero y pulsa «Subir y asociar columnas».
2. Indica qué «Campo del censo» corresponde a cada «Columna de origen», o «No
   importar». El asistente reconoce los nombres habituales en castellano y valenciano.
3. Pulsa «Generar previsualización». **Todavía no se ha modificado el censo.** Verás por
   fila si será alta, actualización o rechazo, y por qué.
4. Corrige el fichero si hace falta y vuelve a subirlo. Si subes el mismo fichero dos
   veces, se muestra el lote existente.
5. Pulsa «Confirmar importación». El informe queda en «Importaciones recientes».

Las cuerdas, los instrumentos y la foto no se importan.

## 2. Invitar a los músicos

Importar **no** envía ninguna invitación. Es una acción aparte:

1. «Miembros» → «Gestionar accesos». Cada persona aparece con su estado: «Sin
   invitar», invitación enviada, «Cuenta activa», «Revocada», «Error de envío» o «Sin
   correo».
2. Marca a quién invitar y pulsa «Enviar o reenviar a seleccionados», o usa «Enviar o
   reenviar a todos los elegibles».
3. Cada persona recibe un enlace válido 7 días para crear su contraseña. Al aceptarlo
   obtiene el rol `member` y su cuenta queda vinculada a su ficha.
4. «Revocar» anula una invitación pendiente. Una invitación ya aceptada no se revoca.

Solo se invita a miembros activos con correo y sin cuenta vinculada. Si hay errores de
envío, el panel lo indica y permite reenviar. El rol `board` también puede invitar,
reenviar y revocar.

## 3. Datos personales y fotos

- Pide solo los datos que la banda necesita de verdad. El DNI y la dirección son
  opcionales.
- La foto de la ficha es **privada**: solo la ven la propia persona y los roles de
  gestión. No se publica nunca en una web.
- Usa datos inventados para probar. No subas un censo real a un entorno de pruebas.

## 4. Fichas: alta, edición, baja y borrado

El alta, la edición, la foto y la baja de una ficha están en
[junta.md](junta.md#8-censo-fichas-de-los-miembros).

**Borrar definitivamente** es solo de `admin` y no se puede deshacer. En la ficha, pulsa
«Borrar esta ficha…» y confirma con «Borrar definitivamente». Solo se permite si la
ficha **no ha dejado rastro**:

- sin convocatorias ni asistencia,
- sin haber recibido encuestas,
- sin transporte asignado ni como conductora,
- sin una cuenta de acceso vinculada.

Si tiene cualquiera de esas cosas, el panel explica el motivo y no la borra: usa
«Dar de baja», que conserva el historial y se puede deshacer. El borrado está pensado
para corregir una ficha creada por error.

## 5. Roles y accesos

Una invitación concede solo el rol `member`. Los demás roles se dan en «Miembros» →
«Accesos y roles» (recorrido en [junta.md](junta.md#9-accesos-y-roles)). Como `admin`,
además puedes conceder y quitar el rol `admin` y desactivar el acceso de otra cuenta de
administración.

- Siempre debe quedar al menos una cuenta de administración activa: el panel no deja
  quitar el rol ni desactivar el acceso del último `admin`.
- Desactivar un acceso no borra la cuenta: la persona puede pertenecer a otras bandas.
- `platform` y `web_editor` los asigna el operador de la plataforma.
- El cargo (presidencia, tesorería…) no da permisos: los da el rol.

## Todavía no se puede

- Dar de alta cuerdas o instrumentos desde el panel.
- Borrar una cuenta: solo se desactiva su acceso a la asociación.
- Restablecer la contraseña de un músico.
