# Manual de contratista y organización (`organizer`)

Para preparar actuaciones y salidas: crear la actividad con su logística, convocar a
la plantilla que hace falta, seguir la disponibilidad y comunicar los cambios. Se
trabaja desde el **panel de la junta**.

El rol `organizer` tiene los mismos permisos en el panel que `board` y `director`. El
paso a paso detallado de cada pantalla está en [junta.md](junta.md). Aquí se cuenta
el recorrido de una actuación.

## Recorrido de una actuación

**1. Crear la actuación en borrador.** En Inicio pulsa «Nueva actividad» y elige tipo
*Actuación*. Lo que el músico necesita saber va en campos propios, para que lo vea en
la app y se avise si cambia:

| Campo | Ejemplo |
| --- | --- |
| Concentración | Hora a la que hay que estar en el punto de salida. |
| Lugar | Plaza, iglesia o pueblo de la actuación. |
| Uniforme | «Gala completa, gorra y zapato negro». |
| Plazo de respuesta | Fecha tope para saber con cuántos cuentas. |
| Asistencia obligatoria | Obliga a justificar las ausencias. |
| Repertorio | Un título por línea; notas tras «\|». |

Revisa el repertorio antes de crear la actuación: hoy no se puede cambiar después desde
el panel.

**2. Convocar a la plantilla.** En el detalle, «Convocar a una selección» permite
componer la formación por cuerdas, instrumentos o personas. Puedes hacerlo en tandas.
Nadie queda convocado dos veces.

**3. Publicar.** «Publicar actividad» avisa a todos los convocados por la app y por
correo.

**4. Seguir la disponibilidad.** La tabla «Convocatorias» muestra la respuesta de cada
persona: pendiente, aceptada o rechazada. El motivo de una ausencia no se ve todavía
en el panel. Si faltan efectivos de un instrumento, convoca a más personas. Cada nueva
convocatoria avisa al momento.

**5. Comunicar cambios.** Con «Cambiar la ficha» → «Guardar y avisar», un cambio de
hora, concentración o lugar avisa a todos los convocados. También devuelve las
respuestas a *pendiente*, porque un «sí» dado para otra hora ya no vale. Si el plazo ya
había vencido, amplíalo al mismo tiempo.

**6. Cancelar.** «Cancelar la actividad» con motivo avisa a todos y conserva el
historial.

**7. El día de la actuación.** Pasa lista en la tabla con «Presente», «Ausente» o
«Ausencia justificada» y pulsa «Guardar». La asistencia real no depende de lo que se
respondió.

## Transporte

El servidor ya guarda el transporte de una actividad: medio (coche, autobús u otro),
punto de encuentro, hora de salida, conductor, plazas y personas asignadas. Comprueba
que no se superen las plazas ni haya asignaciones duplicadas, y cada músico ve su
asignación en la app.

**Todavía no hay pantalla en el panel para organizarlo.** Hasta que exista, la
asignación la carga el operador de la plataforma. No se calculan rutas ni
compensaciones por coche.

## Refuerzos

Un músico de otra banda que viene de refuerzo se da de alta en el censo como
*colaborador musical externo*. Así se le puede convocar sin crear otra asociación ni
darle acceso al resto del censo. El alta la hace la administración
([administracion.md](administracion.md)). Gesband todavía no busca refuerzos entre
bandas.

## Todavía no se puede

- Organizar el transporte desde el panel.
- Duplicar una actuación.
- Ver un recuento de confirmados por cuerda o instrumento: hay que contarlo en la
  tabla.
- Compartir un mensaje preparado por WhatsApp.
- Calcular pagos por actuación o por coche: están fuera del MVP.
