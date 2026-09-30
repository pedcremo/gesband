# Manual de edición web (`web_editor`)

Este rol está reservado para el **complemento web de la asociación**: una web pública
con portada, páginas institucionales, noticias y agenda de actuaciones, descrita en
[ANALISIS.md, sección 5](../../ANALISIS.md#5-complemento-web-de-la-asociación).

**El complemento todavía no existe.** No forma parte del MVP. Hoy el rol se puede
asignar, pero no permite hacer nada en Gesband.

## Qué ve hoy una cuenta con este rol

| Pantalla | Resultado |
| --- | --- |
| Panel de la junta, censo, actividades, encuestas | «Sin permiso» (403) |
| «Mi acceso» (`/panel/me/`) | Muestra el rol y que no concede capacidades |

Es a propósito: editar la web no da acceso al censo ni a la operativa de la banda
([decisión 0002](../decisions/0002-alcance-de-lectura-por-rol.md)). Si la persona
también toca en la banda o está en la junta, tendrá además esos roles y sus manuales.

## Cómo funcionará, según el análisis

Esto es lo previsto, no lo implementado:

- Borrador, previsualización, publicación y retirada de contenidos, con formularios
  estructurados y sin HTML ni scripts arbitrarios.
- Publicar una actuación será una acción explícita que solo copia los datos públicos:
  título, lugar y horario. Nunca se publican convocatorias, respuestas, asistencias,
  transporte, fichas ni fotos privadas.
- Las imágenes públicas se suben aparte y con autorización de publicación. La foto de
  la ficha de un músico nunca pasa a la web.
- Desactivar el complemento retira la web sin afectar a la gestión interna.

Este manual se completará cuando el complemento se construya.
