# Cuerdas comunes e instrumentos precargados

Fecha: 15 de octubre de 2026.

## Contexto

Cada asociación tenía sus propias cuerdas (`Section` con `association`), creadas a mano
o por la importación del censo. Así, la misma cuerda aparecía con nombres distintos en
cada banda («Metal», «Metall», «Vent»…) y una errata del fichero creaba una cuerda
nueva. El promotor indicó el 15 de octubre de 2026 que las cuerdas son genéricas para
todas las asociaciones y fijó la lista. También pidió precargar instrumentos de cada
cuerda con su nombre en castellano, valenciano e inglés.

## Decisión

- Las cuerdas son un **catálogo fijo y común**, sin asociación: Viento metal, Viento
  madera, Percusión, Cuerda frotada, Cuerda percutida y Cuerda pulsada. Cada una tiene
  un código estable (`brass`, `woodwind`, `percussion`, `bowed_strings`,
  `struck_strings`, `plucked_strings`) y su nombre en `es`, `ca` y `en`. Solo se
  cambian con una migración: la API las expone en solo lectura (`GET /api/v1/sections/`)
  y Django Admin solo permite consultarlas.
- Los **instrumentos siguen siendo de cada asociación**: una banda puede tener
  instrumentos propios. `apps/members/catalog.py` define unos cincuenta instrumentos
  predefinidos con código, cuerda, nombres en tres idiomas y alias. Cada banda los
  recibe al migrar y al darse de alta en Django Admin. El comando
  `seed_instrument_catalog` añade a las bandas existentes los que se incorporen después.
- La precarga es idempotente y **no duplica**: si la banda ya tiene un instrumento con
  el nombre, la traducción o un alias de uno predefinido, se vincula a él. Conserva su
  nombre, y su cuerda solo se rellena si no tenía.
- El panel y la API muestran cuerdas e instrumentos en el idioma de la persona, con el
  nombre en castellano como respaldo. Un instrumento propio sin traducción conserva su
  nombre.
- La **importación** reconoce la cuerda por su nombre en cualquiera de los tres idiomas
  o por un alias habitual («Metal», «Madera», «Fusta», «Corda»…). Una cuerda desconocida
  invalida la fila, en lugar de crear una cuerda nueva. Un instrumento predefinido que
  falte se crea con su cuerda del catálogo. Si el fichero le asigna otra cuerda, la fila
  se rechaza. El resultado deja de incluir `sections_created`.

## Migración de los datos existentes

La migración `members.0006` crea las seis cuerdas comunes. Después reasigna cada
instrumento: si su nombre es uno de los predefinidos, toma la cuerda del catálogo. Si
no, toma la que corresponda al nombre de su cuerda antigua. Si ninguna encaja, queda sin
cuerda. Por último borra las cuerdas por asociación y precarga los instrumentos. Las
fichas, sus instrumentos y las convocatorias no cambian. La reversa recrea cuerdas por
asociación con el nombre en castellano.

## Consecuencias

- Convocar o consultar por cuerda sigue limitado a los músicos de la propia
  asociación: la cuerda es común, pero el filtro siempre parte de las fichas e
  instrumentos de la banda.
- Una cuerda nueva, por ejemplo para una formación distinta de la banda, requiere una
  migración y la revisión de los alias.
- La gestión de instrumentos desde el panel sigue pendiente; hasta entonces se usa Django
  Admin.
