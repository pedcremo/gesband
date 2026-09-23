# Localización coherente de la interfaz

Fecha: 21 de septiembre de 2026.

## Contexto

Gesband necesita ofrecer castellano, valenciano e inglés sin mezclar idiomas en una
misma sesión. Django Admin, las plantillas propias, la API y Flutter partían de
mecanismos y textos distintos.

## Decisión

- El castellano (`es`) es el idioma fuente y el predeterminado.
- El valenciano usa el código `ca`, compatible con Django, Flutter y la negociación
  HTTP; sus traducciones emplean formas valencianas.
- El inglés usa el código `en`.
- El panel y Django Admin comparten la elección persistida por `set_language` en el
  navegador.
- Flutter conserva la elección en las preferencias del dispositivo y envía
  `Accept-Language` a la API para recibir también los errores en ese idioma.
- Los textos del servidor se extraen a catálogos de Django y se compilan al construir
  la imagen. Los textos móviles se centralizan en el sistema de localización de la
  aplicación.

Los nombres, lemas, actividades y demás contenido escrito por una asociación no se
traducen automáticamente: se muestran tal como fueron introducidos.

## Consecuencias

Cada texto nuevo visible debe añadirse al mecanismo de traducción correspondiente y
las pruebas deben cubrir los tres idiomas. La preferencia actual es local al navegador
o dispositivo; sincronizarla entre dispositivos requeriría añadirla al perfil de la
cuenta y queda como una ampliación explícita.
