# Encuestas con voto único y anónimo

Fecha: 24 de septiembre de 2026.

## Contexto

ANALISIS.md 3.7 pide encuestas a los miembros con dos condiciones que el servidor
debe garantizar por sí mismo: cada persona vota una vez, y el sistema puede demostrar
que alguien votó sin poder decir qué votó. Dejaba abiertas cuatro decisiones: tipos de
pregunta, quién ve el provisional, si se puede anular una encuesta abierta y qué pasa
con el provisional al vencer el plazo.

## Decisión

### Esquema

Un módulo nuevo, `apps/polls`, con cuatro tablas:

- `Poll`: enunciado, plazo (`closes_at`) y estado `draft → open → published`, o
  `cancelled` desde borrador o abierta.
- `PollOption`: las opciones.
- `PollRecipient`: **participación**. Quién ha sido consultado y un booleano
  `has_voted`. Nada más.
- `Ballot`: **papeleta**. Encuesta y opción. Sin cuenta, sin miembro, sin fecha y con
  clave UUID aleatoria.

Las dos últimas no comparten ninguna columna que permita emparejarlas. Tampoco lo
permite el orden: `Ballot` no tiene fecha ni entero correlativo, y `PollRecipient` no
guarda la hora del voto. Con una hora en cada lado, o con un identificador creciente,
bastaría ordenar las dos tablas para emparejarlas. Hay una prueba (`tests/test_polls.py`,
`BallotsCannotBeLinkedToVotersTests`) que falla si alguien añade una de esas columnas.

El voto se registra en `services.cast_vote` dentro de una transacción, con bloqueo
sobre la fila de participación: dos intentos simultáneos de la misma persona se
serializan y el segundo encuentra `has_voted` ya cierto. La API responde 409.

### Decisiones abiertas de ANALISIS.md 3.7

1. **Tipo de pregunta: opción única.** Opción múltiple y orden de preferencia quedan
   para cuando haya un caso real; el esquema lo admite con varias papeletas por voto,
   pero ahora no hace falta.
2. **Mientras se vota, junta y destinatarios ven lo mismo**: el recuento provisional
   anónimo y el total de votos emitidos. La junta **no** ve quién ha votado hasta que
   se cierra el plazo. Mirar a la vez la lista de participación y cómo se mueve el
   recuento provisional bastaría para deducir el voto de cada persona («Ana acaba de
   votar y Valencia ha subido uno»).
3. **Una encuesta abierta se puede anular**, con motivo obligatorio, y se avisa a los
   destinatarios. Se conservan participación y papeletas, pero ninguna vista muestra el
   recuento de una anulada: no tiene resultado. Un resultado publicado no se anula.
4. **Con el plazo vencido y sin publicar**, los destinatarios dejan de ver el
   provisional y ven «pendiente de publicar». La junta sí lo ve, junto con la lista de
   quién votó y quién no, para revisarlo antes de publicarlo. Así la publicación es el
   momento en que el resultado pasa a ser oficial, como pide el requisito.

Los destinatarios se eligen como en una convocatoria: todos los músicos activos, o una
combinación de cuerdas, instrumentos y personas. Solo cuentan fichas activas de la
asociación; un identificador de otra asociación se ignora. En borrador se pueden
cambiar; al abrir quedan fijos.

Los avisos (apertura, publicación y anulación) reutilizan `Notification` con un campo
nuevo `poll` y `deep_link` `gesband://polls/{id}`. La clave de deduplicación incluye el
suceso, así que repetir una operación no vuelve a avisar.

## Consecuencias

- Un voto emitido no se puede modificar ni retirar, ni siquiera a petición de quien lo
  emitió, porque el sistema no sabe cuál es suyo. Los clientes lo advierten antes de
  confirmar y no guardan la opción elegida.
- **Límites del anonimato.** El esquema impide relacionar voto y votante a quien
  consulte la aplicación o la base de datos con SQL corriente. No protege frente a:
  - quien tenga acceso físico a PostgreSQL y analice el orden de las filas en disco o
    el WAL;
  - quien observe el recuento provisional en el momento exacto en que sabe que otra
    persona vota (inevitable si el provisional es visible);
  - resultados con muy pocos votos: con un solo voto, el resultado lo revela.
  El acceso al servidor ya está restringido por AGENTS.md 5; un umbral mínimo de votos
  para mostrar resultados queda como mejora si una junta lo pide.
- El registro HTTP no incluye cuerpos de petición, así que la opción enviada no queda en
  los logs del proxy ni de Gunicorn. Cualquier registro de depuración que se añada en
  el futuro no debe escribir `option_id` junto a la cuenta.
- Cerrar la votación antes de tiempo no está previsto: cambiaría las reglas para quien
  pensaba votar al final. Si hiciera falta, se anula y se abre otra.
