# Prácticas con el alumnado

Material para usar Gesband como proyecto de clase. Los enunciados para el alumnado
están en valenciano y preparados para subirse a Moodle.

| Archivo | Uso |
| --- | --- |
| `practica_1_git.html` | Enunciado de la práctica 1 (Git, GitHub y conflictos, 2 horas, 6 grupos de 3). Se sube a Moodle como recurso *Archivo*. Si se pega en un recurso *Página*, Moodle puede descartar los estilos, pero el contenido sigue siendo legible. |
| `CHANGELOG.md` | Archivo común: cada grupo añade su línea en primera posición. Provoca conflictos entre grupos a propósito. |
| `equips/grupN.md` | Ficha de cada grupo. Las tres personas escriben un lema distinto en la misma línea: primer conflicto, dentro del grupo. |

## Preparación de la práctica 1 (profesorado)

1. Crear una copia de clase. No usar `pedcremo/gesband`: el alumnado necesita
   permiso de escritura y la práctica llena el historial de ramas.

   ```bash
   gh repo create ORGANIZACION/gesband-practiques --public
   git push https://github.com/ORGANIZACION/gesband-practiques.git main:main
   ```

   La protección de ramas en repositorios privados de una organización gratuita no
   está disponible; con GitHub Education (plan Team) sí. Por eso el ejemplo usa uno
   público. El código ya es público y solo contiene datos sintéticos.

2. Proteger `main`: *Settings → Branches → Add rule*, exigir PR con una aprobación
   e impedir `force push`. Si se exige además que la CI esté en verde, tener en cuenta
   que `Backend CI` solo se ejecuta cuando la PR toca `backend/`.
3. Invitar a las 18 personas como colaboradoras (*Settings → Collaborators*), o
   crear un equipo por grupo en la organización.
4. Publicar en Moodle la URL del repositorio y el enunciado.

La CI ejecuta la suite completa del backend en cada `push` con cambios en
`backend/`. Con 18 personas habrá muchas ejecuciones en paralelo; en un
repositorio público no consumen minutos de pago.

## Mapa de conflictos previstos

Sirve para anticipar dónde se atascarán los grupos en la fase 4.

| Archivo | Grupos | Tipo |
| --- | --- | --- |
| `practicas/CHANGELOG.md` | Todos | Seguro: todos insertan en la misma línea. |
| `practicas/equips/grupN.md` | Dentro de cada grupo | Seguro: el lema está en la misma línea. |
| `backend/config/settings.py` | 3 y 4 | Ambos añaden `GESBAND_VERSION`. Debe quedar una sola vez. El grupo 3 además toca `context_processors`. |
| `backend/templates/members/list.html` | 1 y 5 | Resumen sobre la tabla y columna nueva; conflicto probable si tocan la cabecera o el `colspan`. |
| `backend/config/panel.py` | 1 y 2 (y quizá 6) | Funciones distintas: normalmente se fusiona sola. Útil para explicar que no todo cambio concurrente es un conflicto. |
| `docs/manuales/junta.md` | Varios | Depende de dónde escriba cada grupo. |
| `backend/templates/shared/base.html` | 3 | Solo si otro grupo toca la plantilla base. |

Los enunciados no fijan nombres de funciones ni la ubicación exacta de los cambios,
así que pueden aparecer conflictos distintos. Conviene que la revisión cruzada sea
del grupo siguiente (el 6 revisa al 1): así cada grupo lee código ajeno con el que
probablemente chocará.

Las pruebas completas tardan varios minutos en local. En clase cada grupo ejecuta
solo su módulo `backend/tests/test_practica_gN.py` y el módulo del panel que toca.
