# Actividades remuneradas y lo que se adeuda a cada músico

Fecha: 14 de octubre de 2026.

## Contexto

`ANALISIS.md` dejaba las liquidaciones por actuación fuera del MVP hasta definir sus
reglas con las bandas. El promotor pidió el 14 de octubre de 2026 saber si una
actividad es remunerada y a qué precio, y que cada músico vea cuánto se le adeuda de
las actividades a las que ha asistido. Ese mismo día fijó las reglas mínimas.

## Decisión

- Una actividad puede marcarse como **remunerada** con un **importe único por músico**
  en euros. No hay importes por instrumento, cuerda ni persona.
- Un músico **devenga** el importe de una actividad remunerada no cancelada cuando su
  **asistencia real** está registrada como `present`. La respuesta previa a la
  convocatoria nunca genera importes. Ausente, ausencia justificada o asistencia sin
  registrar no devengan.
- La junta **marca como pagado** a un músico en una actividad, o a todos sus
  presentes a la vez. El pago guarda el importe de ese momento, quién lo registró y
  cuándo. Anular un pago no lo borra: queda anulado con su autor y fecha. Solo puede
  haber un pago vigente por convocatoria.
- **Adeudado** = devengado sin pago vigente, con el importe actual de la actividad.
  Cambiar el importe no altera los pagos ya registrados. Si una asistencia pagada deja
  de ser `present`, el pago se conserva y el panel lo señala como incidencia; el
  adeudado nunca es negativo.
- Marcar y anular pagos, y ver lo adeudado a todos, corresponde a los roles `admin` y
  `board`. Los cargos (por ejemplo, tesorería) no conceden permisos por sí solos. El
  músico solo ve lo suyo: en la app (`GET /api/v1/members/me/earnings`) y en el
  detalle de cada actividad remunerada.
- Registrar un pago no mueve dinero: no hay remesas, banca ni conciliación.

## Consecuencias

- Se amplía el alcance del MVP: la liquidación básica por actuación deja de estar
  fuera. Siguen fuera las cuotas de socios, los recibos, el transporte remunerado
  (coche), las remesas bancarias y la monetización de Gesband.
- Los importes son datos económicos privados: nunca se publican ni aparecen en avisos
  push.
- Las reglas son deliberadamente simples para el piloto. Importes distintos por
  persona o instrumento, retenciones o pagos parciales requerirán una decisión nueva.
