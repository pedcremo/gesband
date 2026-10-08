# Sistema visual de la app y el panel: Escenario, Partitura y Festa

Fecha: 8 de octubre de 2026.

## Contexto

La app Flutter usaba Material por defecto (AppBar, ListTile, azul índigo) y no vestía
la marca de la banda, aunque la decisión [0005](0005-la-marca-de-cada-asociacion.md)
ya lo pedía para el cliente web. El promotor la consideró muy pobre y eligió, el
08/10/2026, una dirección visual llamada **Escenario** como estilo por defecto de
Gesband. Cada asociación puede elegir además **Partitura** o **Festa** y un modo de
color. El servidor expone ambos datos en el objeto asociación:

- `visual_style`: `escenario` (por defecto), `partitura` o `festa`.
- `color_mode`: `system` (por defecto), `light` o `dark`.

Todo va encima de la marca: logotipo, color principal y secundario, y lema.

## Decisión

### Tokens propios que generan el tema

`mobile/lib/core/theme/` contiene el sistema:

- `GesbandTokens` (`ThemeExtension`): colores, tipografías, radios y la regla de
  mayúsculas de cada estilo en claro y en oscuro, ya combinados con la marca.
- `buildGesbandTheme` genera el `ThemeData` a partir de los tokens, de modo que
  botones, campos, diálogos, avisos inferiores y menús heredan el estilo.
- `ThemeController` guarda la marca activa y el modo elegido, y reconstruye los
  temas al cambiar de banda.

Las pantallas leen `GesbandTokens.of(context)` y los componentes de
`mobile/lib/core/ui/` (cabecera de marca, navegación, píldoras de estado,
tarjetas, estados vacío/carga/error). Ninguna pantalla escribe colores ni fuentes.

### Los tres estilos

| | Escenario (por defecto) | Partitura | Festa |
| --- | --- | --- | --- |
| Carácter | Oscuro y contundente | Clásico y editorial | Cálido y popular |
| Display | Big Shoulders Display 800, mayúsculas | Libre Caslon Text | Bricolage Grotesque 800 |
| Texto | Instrument Sans | Public Sans | Figtree |
| Fondo / superficie (claro) | #F4F4F2 / #FFFFFF | #FBFAF7 (papel) / #FFFFFF | #F5F6FA / #FFFFFF |
| Fondo / superficie (oscuro) | #0F1012 / #1B1D21 | #171512 / #211E1A | #121419 / #1C1F26 |
| Radios (tarjeta / botón) | 16 / 14 | 14 / 10 | 24 / píldora |
| Cabecera | Logotipo y nombre condensado | Monograma con anillo secundario, lema en cursiva y pentagrama | Bloque del principal con la «faja» diagonal del secundario |
| Próxima convocatoria | «Cartel» del color principal con el día gigante al 16 % y rejilla 2×2 | Tarjeta con filete y columna de fecha | Tarjeta tipo entrada con la fecha teñida |
| Navegación | Cápsula flotante, activo relleno del principal | Barra con filete, activo en color | Barra redondeada, activo con píldora teñida |

Escenario sigue `B-Agenda`; Partitura, `Main`; Festa, `C-Agenda`. Las maquetas solo
traían Partitura y Festa en claro: sus oscuros se derivan conservando el carácter.

Las pantallas son las que ya existían más dos secciones que el contrato y el servidor
ya ofrecían: **Avisos** (`GET /notifications/`) y **Mi ficha** (`GET /members/me/`),
que además aloja los ajustes del dispositivo. No hay «Repertorio» propio: el programa
de cada actividad se muestra en su detalle.

### Legibilidad del color de la banda

Sigue la decisión 0005: el color se usa tal cual solo para fondos.

- `onPrimary` es la tinta que más contrasta con el principal; si ni la oscura del
  tema ni el blanco llegan a 4.5:1 (grises medios), negro o blanco puros.
- `primaryText` es el principal acercado a negro o a blanco hasta 4.5:1 con el fondo
  del modo. Es el `primary` del `ColorScheme`, de modo que Material nunca pinta texto
  con el color sin corregir.
- `primaryOnInk` (botón invertido del cartel) y `onPrimaryTint` (texto sobre el
  tinte) se corrigen igual.
- El borde que resalta lo que espera respuesta usa el secundario corregido a 3:1 con
  la superficie.

### Principal que se funde con el fondo

La banda piloto, Unió Musical de Bocairent, usa #111111 y #C9A227. En oscuro, una
superficie rellena del principal (el cartel, la pestaña activa, el bloque del
logotipo, los botones rellenos) desaparece sobre #0F1012 o #1B1D21.

Regla (`primaryEdgeFor`): si el principal no alcanza **1.5:1** con el fondo o la
superficie del modo, esas superficies llevan un borde de 2 dp del **secundario**; si
el secundario tampoco alcanza 1.5:1, del color de **línea** del tema. En claro el
negro contrasta y no lleva borde.

### Modo de color

Manda el `color_mode` de la banda (`system` sigue al dispositivo). La persona puede
fijarlo en *Mi ficha → Apariencia*: «Como la banda», «Claro» u «Oscuro». La elección
se guarda en el dispositivo (`SharedPreferences`), no en el servidor.

### Marca antes de elegir banda

La marca de la última banda (colores, estilo, modo, lema y logotipo si ocupa hasta
120 KB) se guarda en el dispositivo y viste el acceso y el selector de banda. Sin
nada guardado se usa Gesband con Escenario. Al cerrar sesión se conserva, como en
el cliente web.

### Logotipos y fotos

El logotipo y la foto del músico son privados y se descargan con la sesión. La app
solo acepta URL del mismo host bajo el prefijo del API y hace la petición contra la
base configurada, así que el token no puede salir hacia otro sitio. Los logotipos
(a menudo monocromos y cuadrados, como la lira blanca sobre negro de Bocairent) se
recortan con esquinas redondeadas; sin logotipo, monograma con las iniciales
significativas («UM»).

### Fuentes

Las seis familias son OFL y van empaquetadas, sin descarga en tiempo de ejecución,
para que la app funcione sin conexión. Se instancian solo los pesos usados a partir
de las variables de github.com/google/fonts (≈1 MB). Procedencia y licencias en
`mobile/assets/fonts/README.md`; la app las muestra en *Mi ficha → Licencias*.

### Accesibilidad

Dianas de al menos 48 dp, `Semantics` en botones de icono, encabezados y estados;
el texto en mayúsculas de Escenario se anuncia con su forma original. Las pruebas
recorren las pantallas principales con escala de texto 1.5 y los tres idiomas.

## Consecuencias

- Un estilo o color nuevo se añade en los tokens y lo heredan todas las pantallas.
- Las pruebas de widgets usan `findTextAnyCase` cuando el estilo pone un título en
  mayúsculas, y un móvil alto cuando necesitan que la pantalla entera esté
  construida.
- El cliente web del músico (`/app/`, decisión 0004) todavía no usa estos estilos.
- Pendiente: cambiar la foto desde la app y presentar las horas en la zona horaria de
  la asociación en lugar de la del móvil.

## El panel de la junta (añadido el 08/10/2026)

El panel usa el mismo sistema, trasladado a CSS en `backend/static/panel/panel.css`:

- `<html data-style="escenario|partitura|festa" data-mode="system|light|dark">` elige
  el estilo y el modo. La plantilla base los escribe con `{% brand_attributes %}`
  (`apps/associations/templatetags/panel_shell.py`), junto con las variables de marca.
- `apps/associations/branding.py` calcula en el servidor la misma legibilidad que la
  app: tinta sobre el principal y el secundario, versión corregida a 4.5:1 para texto
  en claro y en oscuro, y el filo (`--brand-edge-*`) cuando el principal no llega a
  1.5:1 con el fondo. Bocairent (#111111 / #C9A227) lleva filo dorado en oscuro.
- Las fuentes se sirven desde el propio servidor (`backend/static/panel/fonts/`, OFL),
  sin pedirlas a Google desde el navegador de cada persona.
- La portada es el «cartel» de la próxima actividad publicada con el recuento de
  respuestas, las siguientes en tarjetas y las anteriores en tabla.
- El acceso y la activación de cuenta usan una base sencilla (`shared/plain.html`);
  la activación se viste con la marca de la banda que invita.

### Imagen de la banda

`/panel/branding/` permite a `admin` y `board` (permiso nuevo `branding.manage`)
cambiar logo, colores, lema, estilo y modo, con vista previa al momento. La regla
vive en `apps/associations/services.update_branding`. El logo se valida por su
contenido, se reescala a 1024 px como máximo, pierde los metadatos y se guarda como
WebP sin pérdida con transparencia y nombre interno. Se sirve, como antes, solo a
quien pertenece a la asociación (`/api/v1/associations/{id}/logo/`).
