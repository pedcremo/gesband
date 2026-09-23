# Avisar de los cambios y las cancelaciones de una actividad

Fecha: 23 de septiembre de 2026.

## Contexto

Una actividad publicada se podía editar sin que nadie se enterara. `PATCH` y la
acción de publicar subían `Activity.version` y guardaban, pero no creaban ningún
aviso: quien ya había aceptado una actuación seguía con la fecha, el lugar y el
uniforme antiguos en la app.

Tampoco había forma de cancelar avisando. El estado era escribible desde `PATCH`,
así que una cancelación era un cambio de campo silencioso.

`contracts/openapi.yaml` ya describía el comportamiento correcto —
`cancelActivity` y «Edita actividad y genera avisos si cambia información
relevante»— pero el servidor no lo implementaba.

## Decisión

Un cambio se avisa cuando toca algo que la persona convocada necesita saber:
título, inicio, final, concentración, lugar, uniforme, plazo de respuesta o
asistencia obligatoria. La descripción y el repertorio no generan aviso.

Cambiar el inicio, la concentración o el lugar además devuelve todas las
respuestas a pendiente. Quien aceptó lo hizo contando con otra fecha u otro sitio,
así que su «sí» ya no significa lo mismo. Cada respuesta anulada queda registrada
en `InvitationResponseEvent`: la convocatoria guarda la respuesta vigente y el
historial vive en los eventos.

El estado deja de ser escribible desde la API. Se cambia con `publish` o con
`cancel`, que avisan por su cuenta. Cancelar exige un motivo, como pedía el
contrato: quien tenía la fecha apartada merece saber por qué deja de estarlo.

Una actividad en borrador no genera avisos: todavía no hay nadie a quien
rectificar. Publicarla avisa a quien se convocó mientras era borrador.

## Consecuencias

La junta puede cambiar y cancelar desde el panel y desde la API, y en ambos casos
se le dice a cuántas personas se ha avisado y cuántas respuestas se han anulado.

Si el plazo de respuesta ya venció cuando se anulan las respuestas, nadie puede
reconfirmar. El panel lo advierte y pide ampliar el plazo; no se amplía solo,
porque la fecha límite es una decisión de la junta.

Queda pendiente la parte móvil: la app muestra el estado y la respuesta que
devuelve la API, pero no destaca todavía una actividad que pide reconfirmación.

## Nota sobre las entregas

`deliver_email_task` existía y no lo invocaba nadie, de modo que las filas de
`Delivery` de correo se quedaban en `pending` para siempre y ningún aviso salía
por correo. `queue_notification_deliveries` las encola ahora al confirmar la
transacción. Se encolan solo las pendientes: la unicidad de `Delivery` no separa
dos filas de correo del mismo aviso, porque su `device` es nulo, y reencolar
todos los avisos de una actividad habría reenviado los cambios anteriores.
