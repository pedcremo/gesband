# El cascarón sin conexión se versiona con su contenido

Fecha: 23 de septiembre de 2026.

## Contexto

El service worker del cliente del músico guardaba el cascarón bajo un nombre de
caché fijo, `gesband-shell-v1`, y respondía a todo lo que no fuera `/api/` desde la
caché antes que desde la red.

Un service worker sólo se reinstala cuando cambia su propio texto, y los ficheros
estáticos no llevan hash en el nombre (`STATIC_URL` sin `ManifestStaticFilesStorage`,
`config/settings.py:133`). Las dos cosas juntas dejaban a quien ya hubiera abierto la
aplicación con la versión que descargó el primer día, para siempre: ningún despliegue
posterior de `app.css` o `app.js` le llegaba nunca.

Se detectó al fotografiar el rediseño: las capturas seguían mostrando la interfaz
vieja después de desplegar la nueva.

## Decisión

`shell_version()` resume con blake2s el contenido de los ficheros del cascarón y
devuelve dieciséis dígitos. Esa huella nombra la caché y acompaña como `?v=` a las
URL, tanto en el service worker como en la página, de modo que ambos piden lo mismo.

Al cambiar cualquiera de esos ficheros cambia el texto del service worker; el
navegador lo detecta, instala, borra las cachés con otro nombre y toma el control.

## Consecuencias

- Un despliegue llega al dispositivo en la siguiente visita, sin pedir a nadie que
  desinstale la aplicación ni vacíe la caché.
- La huella se calcula una vez por proceso salvo con `DEBUG`, donde se recalcula
  para no obligar a reiniciar mientras se trabaja.
- Sigue sin haber hash en el nombre de los ficheros estáticos: si algún día se
  activa `ManifestStaticFilesStorage`, esta huella deja de hacer falta.
