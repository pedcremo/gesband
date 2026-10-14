# Ficheros de ejemplo

Datos **sintéticos** para demostraciones y pruebas. Ninguna persona es real: los
nombres son inventados, los correos usan el dominio reservado `.invalid` (no se
puede entregar nada a esas direcciones) y los teléfonos son del rango ficticio
`+34 600 000 0xx`. La columna DNI va vacía a propósito.

## `musicos-sinteticos.csv`

50 músicos de una banda valenciana con todas las cuerdas e instrumentos básicos,
en una proporción realista (muchos clarinetes, una sola tuba):

| Cuerda | Instrumentos |
| --- | --- |
| Madera | Flauta, Flautín, Oboe, Fagot, Clarinete, Requinto, Clarinete bajo, Saxo alto, Saxo tenor, Saxo barítono |
| Metal | Trompeta, Fliscorno, Trompa, Trombón, Bombardino, Tuba |
| Percusión | Caja, Bombo, Platos, Timbales, Láminas |

Dos filas traen varios instrumentos en la misma celda (`Flauta; Flautín` y
`Caja / Láminas`); el primero queda como instrumento principal. Los
identificadores externos llevan el prefijo `DEMO-` y el tipo de miembro usa los
códigos del importador (`musician` para músico socio, `external` para
colaborador musical externo).

### Cómo importarlo

1. En el panel de la junta, con rol `admin`, abre **Miembros → Importar miembros**.
2. Sube `docs/ejemplos/musicos-sinteticos.csv`. Las cabeceras se asignan solas a
   los campos del censo; revisa la asignación y pulsa **Generar previsualización**.
3. La previsualización no crea fichas ni catálogo: muestra cada fila y el resumen
   de las cuerdas e instrumentos que se añadirán al catálogo de la banda.
4. Pulsa **Confirmar importación**. En una banda sin catálogo se crean 50 fichas,
   3 cuerdas y 21 instrumentos.

Volver a subir exactamente el mismo fichero muestra el lote ya existente. Si se
modifica y se importa de nuevo, las fichas se actualizan por `external_id` sin
duplicarse; los instrumentos de la celda sustituyen a los de la ficha.

La prueba `backend/tests/test_member_import_catalog.py` importa este fichero y
comprueba las altas y el catálogo creado.
