# Prácticas con el alumnado

Material para usar Gesband como proyecto de clase. Los enunciados para el alumnado
están en valenciano y preparados para subirse a Aules FP (el Moodle de la Conselleria).

| Archivo | Uso |
| --- | --- |
| `practica_1_git.html` | Enunciado de la práctica 1 (Git, GitHub y conflictos, 2 horas, 6 grupos de 3). Se sube a Aules FP como recurso *Archivo*. Si se pega en un recurso *Página*, Aules FP puede descartar los estilos, pero el contenido sigue siendo legible. |
| `CHANGELOG.md` | Archivo común: cada grupo añade su línea en primera posición. Provoca conflictos entre grupos a propósito. |
| `equips/grupN.md` | Ficha de cada grupo. Las tres personas escriben un lema distinto en la misma línea: primer conflicto, dentro del grupo. |

## Preparación de la práctica 1 (profesorado)

1. Copia de clase: [`pedcremo/gesband_practicas`](https://github.com/pedcremo/gesband_practicas),
   creada el 21/10/2026 desde `main` de `pedcremo/gesband`. No usar `pedcremo/gesband`:
   el alumnado necesita escritura y la práctica integra en `main` ramas y PR que no
   deben llegar al producto ni al despliegue del piloto. No es un fork porque GitHub
   no permite hacer un fork de un repositorio propio en la misma cuenta. Para
   recrearla otro curso:

   ```bash
   gh repo create pedcremo/gesband_practicas --public
   git push https://github.com/pedcremo/gesband_practicas.git main:main
   ```

   Es pública porque la protección de ramas no está disponible en repositorios
   privados de cuentas gratuitas. El código ya es público y solo tiene datos sintéticos.

2. Proteger `main` (ya hecho en la copia actual): *Settings → Branches → Add rule*,
   exigir PR con una aprobación e impedir `force push`. Si se exige además que la CI esté en verde, tener en cuenta
   que `Backend CI` solo se ejecuta cuando la PR toca `backend/`.
3. Recoger en Aules FP el usuario de GitHub y el grupo de cada persona (fase 0 del
   enunciado) e invitarlas como colaboradoras (*Settings → Collaborators*), por ejemplo:

   ```bash
   gh api -X PUT repos/pedcremo/gesband_practicas/collaborators/USUARIO -f permission=push
   ```

   Las invitaciones caducan a los 7 días. En un repositorio personal, colaborador
   implica escritura; `main` queda protegida por la regla del paso 2, que no se aplica
   al propietario.
4. Publicar el enunciado en Aules FP.

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
