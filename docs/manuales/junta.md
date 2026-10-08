# Manual de la junta (`board`)

Para planificar ensayos y actuaciones, convocar, pasar lista, consultar a la banda con
encuestas, mantener el censo y gestionar quién entra en la asociación. Se trabaja desde
el **panel de la junta**, en un ordenador o una tableta.

El rol `board` comparte con `organizer` y `director` las actividades, las encuestas y
las fichas del censo. Además, como `admin`, invita a los músicos y gestiona accesos y
roles (apartado 9), salvo el rol de administración. La importación del censo, el borrado
definitivo de fichas y la configuración de la asociación son solo de `admin`
([administracion.md](administracion.md)).

Si además tocas en la banda, tu cuenta tendrá también el rol `member`: consulta
[musico.md](musico.md) para la app móvil.

## 1. Entrar

1. Abre `/accounts/login/`, escribe tu **correo electrónico** (o tu usuario, si te lo
   dieron) y tu contraseña y pulsa «Iniciar sesión».
2. Llegas a **Inicio**, el panel de tu banda, con la lista de actividades: fecha,
   número de convocados y estado.
3. La cabecera tiene «Inicio», «Miembros», «Encuestas», «Mi acceso», el selector de
   idioma y «Cerrar sesión».

## 2. Crear una actividad

1. En Inicio, pulsa «Nueva actividad».
2. Elige el tipo (ensayo o actuación) y rellena título, inicio, final, concentración,
   lugar, uniforme, plazo de respuesta, «Asistencia obligatoria» y descripción. Las
   horas se escriben en la hora local de la asociación.
3. **Repertorio** (opcional): un título por línea. Para añadir una nota, escríbela tras
   «|», por ejemplo `Paquito el chocolatero | de pasacalle`.
4. Pulsa «Crear en borrador». Un borrador no avisa a nadie.

Validaciones: el final no puede ser anterior al inicio, la concentración no puede ser
posterior al inicio y el plazo de respuesta debe terminar antes de la actividad.

## 3. Convocar

En el detalle de la actividad, apartado «Convocar músicos»:

- **«Convocar a todos los músicos activos».**
- **«Convocar a una selección»**: marca cuerdas, instrumentos o personas. Se convoca a
  quien cumpla cualquiera de las casillas. Solo cuentan los músicos activos, y quien
  ya estaba convocado no se duplica.

Al convocar puedes marcar «Actividad obligatoria: una ausencia deberá justificarse».
Entonces, quien responda que no asistirá tendrá que escribir el motivo.

Puedes convocar en varias tandas, por ejemplo primero la percusión y luego a una
persona suelta. Mientras la actividad está en borrador, nadie recibe aviso.

## 4. Publicar

Pulsa «Publicar actividad». Se avisa a todas las personas convocadas, por la app y por
correo. A partir de entonces, cada nueva convocatoria avisa al momento.

## 5. Cambiar o cancelar una actividad publicada

**«Cambiar la ficha» → «Guardar y avisar».**

- Avisa a los convocados si cambias título, inicio, final, concentración, lugar,
  uniforme, plazo o asistencia obligatoria.
- Si cambias **inicio, concentración o lugar**, además todas las respuestas vuelven a
  *pendiente* y se pide confirmar de nuevo. Las respuestas anteriores quedan en el
  historial.
- Si el plazo de respuesta ya ha vencido, el panel te lo advierte: amplíalo o nadie
  podrá reconfirmar.
- La descripción no genera aviso. El repertorio no se puede cambiar desde el panel.

**«Cancelar la actividad».** Escribe el motivo, que va incluido en el aviso, y pulsa
«Cancelar y avisar». No se borra nada: la actividad queda como cancelada con su
historial.

## 6. Seguir las respuestas y pasar lista

En la tabla «Convocatorias» del detalle ves, por cada músico, su **respuesta** (la
previsión que da en la app: pendiente, aceptada o rechazada) y su **asistencia** real.

Para pasar lista, elige en cada fila «Presente», «Ausente», «Ausencia justificada» o
«Sin registrar» y pulsa «Guardar». Queda registrado quién lo anotó.

La respuesta y la asistencia son independientes: alguien que dijo «no» puede aparecer
y alguien que dijo «sí» puede faltar.

## 7. Encuestas

En «Encuestas» → «Nueva encuesta»:

1. **Borrador:** enunciado, descripción opcional, «Cierre de la votación» y opciones,
   una por línea y al menos dos. Pulsa «Guardar borrador». Mientras sea borrador,
   puedes corregirla o borrarla («Borrar borrador»).
2. **Destinatarios:** en «A quién se consulta» marca todos los músicos activos, cuerdas,
   instrumentos o personas y pulsa «Guardar destinatarios». La selección sustituye a la
   anterior.
3. **Abrir:** «Abrir votación y avisar». Desde ese momento la encuesta ya no se puede
   corregir y se avisa a los destinatarios.
4. **Mientras se vota** ves el mismo recuento provisional que los destinatarios, pero
   **no quién ha votado**: junto al provisional delataría el voto de cada persona.
5. **Al vencer el plazo** aparece «Plazo vencido, pendiente de publicar». Solo la junta
   ve el recuento y «Quién ha votado». Revísalo y pulsa «Publicar resultado». La
   publicación es definitiva y avisa a los destinatarios.
6. **Anular:** una encuesta abierta se puede anular con «Anular y avisar», indicando el
   motivo. Un resultado publicado no se anula.

**El voto es anónimo.** El sistema sabe quién ha votado, pero no qué ha votado cada
persona. Por eso nadie puede cambiar ni retirar un voto emitido, tampoco a petición de
quien lo emitió.

## 8. Censo: fichas de los miembros

«Miembros» lista la banda: nombre, tipo (músico socio, socio colaborador/mecenas o
colaborador musical externo), instrumento y estado. Pulsa un nombre para abrir su ficha.

**Dar de alta.** «Miembros» → «Nueva ficha». Solo son obligatorios el nombre y los
apellidos. Puedes indicar el identificador externo (número de socio, único dentro de la
banda), tipo, estado, correo, teléfono, dirección, DNI/NIE si la banda lo necesita,
instrumentos, instrumento principal (su cuerda es la que cuenta al convocar por cuerdas)
y cargos. Pulsa «Crear ficha». Crear una ficha no envía ninguna invitación.

**Editar.** En la ficha cambia lo que haga falta y pulsa «Guardar cambios». Si algo no
es válido, por ejemplo un número de socio repetido, el panel lo indica junto al campo y
no guarda nada.

**Cargos.** Presidencia, vicepresidencia, secretaría, tesorería, contratista y vocalía
son informativos: **no dan permisos**. Los permisos se dan con roles (apartado 9).

**Foto.** En «Foto», elige un JPEG, PNG o WebP de hasta 5 MB y pulsa «Subir foto» o
«Sustituir foto». Se comprueba que sea una imagen real, se quitan sus metadatos y solo
la ven la propia persona y quien gestiona la banda. «Eliminar foto» la borra.

**Dar de baja y reactivar.** «Dar de baja» pide confirmación y deja la ficha
*inactiva*: ya no se la puede convocar ni invitar, pero se conservan sus convocatorias,
respuestas, asistencia, encuestas y transporte. «Reactivar» la devuelve a activa. La
ficha muestra quién hizo el último cambio de estado y cuándo.

El borrado definitivo de una ficha es solo de `admin`.

## 9. Accesos y roles

La ficha es el registro en el censo; la cuenta es el acceso. Con el rol `board` puedes:

- **Invitar** a los músicos a crear su cuenta, reenviar y revocar invitaciones:
  «Miembros» → «Gestionar accesos». El recorrido está en
  [administracion.md](administracion.md#2-invitar-a-los-músicos).
- **Conceder y quitar roles:** «Miembros» → «Accesos y roles». En cada cuenta elige un
  rol y pulsa «Conceder rol», o pulsa «Quitar» junto a un rol y confírmalo. Puedes dar
  `member`, `board`, `organizer` y `director`.
- **Desactivar y reactivar un acceso:** «Desactivar» (con confirmación) impide a esa
  cuenta entrar en esta banda, sin borrar la cuenta ni tocar sus otras bandas.
  «Reactivar» lo deshace.

Límites que aplica el servidor:

- El rol `admin` solo lo concede o lo quita alguien con `admin`, y solo `admin` puede
  desactivar el acceso de otra cuenta que lo tenga.
- Siempre debe quedar al menos una cuenta de administración activa.
- No puedes desactivar tu propio acceso.
- Los roles `platform` y `web_editor` los asigna el operador de la plataforma.

Al final de la página, «Últimos cambios» muestra quién concedió o quitó cada rol y quién
activó o desactivó cada acceso.

## 10. Compartir por WhatsApp

Todavía no hay una función de «compartir mensaje preparado». De momento, copia el texto
de la actividad y compártelo tú desde WhatsApp. Gesband no envía nada por WhatsApp.

## Todavía no se puede

- Editar el repertorio después de crear la actividad (hay que hacerlo desde la
  administración interna).
- Duplicar una actividad para repetir un ensayo habitual.
- Ver un resumen de confirmaciones y asistencias por cuerda o instrumento.
- Organizar el transporte desde el panel. Existe en el servidor, pero todavía no tiene
  pantallas; ver [organizacion.md](organizacion.md).
- Importar el censo o borrar definitivamente una ficha: es de `admin`.
- Conceder o quitar el rol `admin`.
- Dar de alta cuerdas o instrumentos desde el panel.
- Gestionar cuotas, pagos o liquidaciones: están fuera del MVP.
