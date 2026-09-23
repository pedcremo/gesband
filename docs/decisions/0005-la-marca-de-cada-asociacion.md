# La aplicación del músico se viste con la marca de cada asociación

Fecha: 23 de septiembre de 2026.

## Contexto

El cliente web del músico se construyó pensando sólo en recorrer la funcionalidad,
con un azul fijo y sin identidad. El promotor lo rechazó por su aspecto: *«La web
es más fea que pegarle a un padre. Son artistas los músicos, así que le pido un
poco de sensibilidad. No todo está en la funcionalidad. La estética aquí importa».*

Además incumplía un requisito escrito del propio encargo, `README.md:34`: *«Quiero
q la aplicación sea configurable con el logo y el esquema de color y lemas q escoja
cada asociación»*, recogido en `ANALISIS.md:28` y `ANALISIS.md:56`. Los datos ya
estaban en el modelo (`apps/associations/models.py:13-27`) y en la API
(`apps/api.py`), pero la interfaz los ignoraba.

## Decisión

La asociación pone la cara y la aplicación se adapta:

- El color principal y el secundario llegan del API y se inyectan como variables
  CSS. El logotipo y el lema encabezan la pantalla de acceso y la cabecera.
- Cuando no hay logotipo se compone un monograma con las iniciales del nombre.
- La marca de la última asociación se guarda en `localStorage`, de modo que quien
  vuelve a entrar ve su banda antes de escribir la contraseña. Si no hay nada
  guardado, la pantalla es la de Gesband.

### El color nunca se usa tal cual para texto

`ANALISIS.md:56` pide configurar los colores *«con límites que mantengan
legibilidad»*. El límite se aplica al pintar, no al elegir: una banda puede tener
el amarillo o el negro que quiera en su escudo.

`aplicarMarca` calcula la luminancia relativa del color y deriva cuatro variables:
el color tal cual para fondos, la tinta legible encima de él, un tinte suave para
superficies, y una versión corregida —acercada a blanco o a negro— para el texto,
que sólo se acepta cuando contrasta 4.5:1 con el fondo sobre el que se va a leer.
Los neutros del modo oscuro se invierten en CSS y las variables de marca se
recalculan contra ese fondo.

### El logotipo se sirve por la API

El contrato (`contracts/openapi.yaml:1153`) definía `logo_url`, pero el serializador
exponía el campo `logo` en crudo, que resolvía a `/media/…`: una ruta que nadie
sirve, porque los ficheros viven en media privada. El logotipo se sirve ahora desde
`/api/v1/associations/{id}/logo/`, igual que la foto del músico, y sólo lo ve quien
pertenece a la asociación. Manda el contrato, como fija `AGENTS.md` §6.

## Consecuencias

- El cliente pide el logotipo con el token y lo muestra desde un blob; si pesa menos
  de 120 KB lo guarda también para la pantalla de acceso.
- La agenda se agrupa por meses y cada convocatoria lleva su bloque de fecha, el
  estado de la respuesta en el filo de la tarjeta y el lugar. El idioma y la salida
  se han movido a «Mi ficha», que es donde se esperan unos ajustes.
- Queda fuera: el panel de la junta sigue sin vestir la marca.
