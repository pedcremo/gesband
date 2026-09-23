# Cliente web del músico para desarrollo

Fecha: 23 de septiembre de 2026.

## Contexto

El recorrido del músico solo se podía probar con `curl`. El cliente Flutter de
`mobile/` no tiene andamiaje de plataforma —no existen `android/`, `ios/` ni
`web/`—, así que no se puede ejecutar en ningún sitio, y ponerlo en marcha exige
instalar el SDK de Android y disponer de un proyecto Firebase.

Hacía falta recorrer el producto desde el papel del músico a un nivel más alto
que las llamadas sueltas a la API, sin esperar a esas dos cosas.

## Decisión

Una aplicación web servida por Django en `/app/`, en HTML, CSS y JavaScript sin
framework ni paso de compilación, que habla con `/api/v1/` igual que lo hará la
app móvil.

Vive en el mismo origen que la API, de modo que no hace falta CORS. No usa la
sesión del panel: guarda el token en `localStorage` y ejercita el mismo camino de
autenticación que el cliente móvil. Es instalable —manifiesto y *service
worker*— y el cascarón funciona sin conexión; las respuestas de la API nunca se
sirven de caché, porque una convocatoria caducada engañaría a quien la lea.

El *service worker* se sirve desde `/app/sw.js` y no desde `/static/`: su alcance
es la ruta desde la que se entrega, y desde `/static/` no cubriría la aplicación.

Cubre el recorrido del músico: acceso, elección de asociación, agenda, detalle de
la actividad, respuesta a la convocatoria, bandeja de avisos y ficha propia, en
castellano, valenciano e inglés.

## Qué no es

No sustituye al cliente Flutter: cuando `mobile/` se pueda ejecutar, la app móvil
sigue siendo el producto. Tampoco es el complemento web de la asociación de
`ANALISIS.md` 5, que es un sitio público con otro propósito y otras reglas de
publicación.

Es una herramienta de desarrollo y así debe tratarse: no se anuncia a las bandas
ni se cuenta como entregable del piloto.

## Consecuencia sobre la API

Un cliente no podía distinguir «todavía no he contestado» de «me han anulado el
sí porque cambió la fecha»: ambas situaciones son `response: pending`. La
convocatoria expone ahora `needs_reconfirmation`, cierto cuando está pendiente y
tiene respuestas anteriores en el historial, y `activity_version`, que el
contrato ya preveía como `revision`. La app móvil lo necesitará igual.
