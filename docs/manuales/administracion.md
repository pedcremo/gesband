# Manual de administración de la asociación (`admin`)

Para cargar y mantener el censo, invitar a los músicos a usar la app y configurar la
asociación. Además, `admin` puede hacer todo lo de la junta: actividades,
convocatorias, asistencia y encuestas, descritas en [junta.md](junta.md).

Lo que solo puede hacer `admin`:

| Tarea | Dónde |
| --- | --- |
| Importar miembros desde CSV o XLSX | «Miembros» → «Importar miembros» |
| Invitar a los músicos a crear su cuenta | «Miembros» → «Gestionar accesos» |
| Configurar la asociación: nombre, logo, colores, lema | Mediante el operador de la plataforma (ver al final) |

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
envío, el panel lo indica y permite reenviar.

## 3. Datos personales y fotos

- Pide solo los datos que la banda necesita de verdad. El DNI y la dirección son
  opcionales.
- La foto de la ficha es **privada**: solo la ven la propia persona y los roles de
  gestión. No se publica nunca en una web.
- Usa datos inventados para probar. No subas un censo real a un entorno de pruebas.

## 4. Roles de la junta

Una invitación concede solo el rol `member`. Para que alguien gestione (`board`,
`organizer`, `director` o `admin`), pide al operador de la plataforma que se lo asigne.
Recuerda que el cargo (presidencia, tesorería…) no da permisos: los da el rol.

## Todavía no se puede

- Editar una ficha, sus instrumentos o su foto desde el panel.
- Dar de baja o de alta a una persona desde el panel.
- Asignar roles de junta desde el panel.
- Cambiar el logo, los colores o el lema desde el panel: lo hace el operador de la
  plataforma.
- Restablecer la contraseña de un músico.
- Las personas que activan su cuenta con una invitación todavía no pueden entrar en el
  panel, porque este pide el usuario y no el correo. Mientras no se corrija, las cuentas
  de la junta las crea el operador de la plataforma.
