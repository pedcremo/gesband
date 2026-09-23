# Instrucciones de desarrollo de Gesband

## 1. Contexto y prioridad

Lee `ANALISIS.md` completo antes de iniciar trabajo de producto o arquitectura. `README.md` conserva la petición original; `ANALISIS.md` recoge su evolución hacia un MVP para validar aceptación. Las instrucciones explícitas más recientes del usuario prevalecen.

El repositorio está en fase de definición. Las rutas y comandos siguientes describen la estructura prevista; no supongas que existen componentes, dependencias, servicios o pruebas hasta comprobarlo.

Objetivo actual: completar y validar el recorrido de importar miembros, planificar actividades, convocar, responder, comunicar cambios y registrar asistencia.

Límites de alcance:

- Incluir foto privada opcional del músico y personalización por asociación.
- Cumplir MUST-NOTIF-01 de `ANALISIS.md`: activación guiada, comprobación de permiso y registro push, recuperación desde ajustes y prueba real en Android/iOS antes del piloto. No rebajar este requisito a una mejora opcional ni sustituirlo por correo.
- Incluir transporte básico y repertorio como lista de títulos y notas.
- Incluir encuestas a los miembros según `ANALISIS.md` 3.7, añadidas el 23/09/2026. El voto único y el anonimato son requisitos del servidor, no del cliente: el registro de participación y las papeletas no pueden compartir clave.
- Prescindir de Hitobito y otros productos base en esta etapa.
- No implementar monetización, periodos comerciales de prueba, checkout, precios ni bloqueo por impago.
- No implementar todavía cuotas, liquidaciones ni pagos bancarios. Son funciones de las asociaciones, distintas de la futura monetización de Gesband.
- Documentar y preservar el encaje del complemento web; no construirlo hasta que una tarea lo incluya expresamente.
- WhatsApp en el MVP significa compartir manualmente mensajes preparados. No implica envío automático ni confirmación de entrega.

## 2. Arquitectura acordada

- Flutter/Dart para Android e iOS con código común.
- Django y Django REST Framework para servidor y API.
- PostgreSQL como base de datos del dominio.
- Panel de junta con vistas propias de Django; mejora progresiva y HTMX solo si aporta simplicidad.
- Django Admin para operación interna restringida, no como sustituto del panel de la junta.
- Celery y RabbitMQ para trabajos asíncronos.
- Firebase Cloud Messaging y APNs para push; SMTP transaccional configurable para correo.
- Docker Compose en Ubuntu para los entornos desplegados.
- Backend modular único y API `/api/v1/`; evitar servicios independientes sin una necesidad demostrada.

Reutiliza dependencias mantenidas. No crees autenticación, criptografía o protocolos de mensajería propios. Fija las versiones soportadas y los archivos de bloqueo al crear cada componente.

## 3. Estructura prevista y propiedad

```text
backend/
  config/                       Configuración global y rutas
  apps/
    accounts/                   Identidades, autenticación e invitaciones de acceso
    associations/               Asociaciones, roles y personalización
    members/                    Censo, instrumentos, fotos e importación
    activities/                 Ensayos, actuaciones, convocatorias y asistencia
    transport/                  Transporte y asignaciones por actividad
    communications/             Avisos, entregas, dispositivos y trabajos de envío
    website/                    Complemento futuro; no crear por anticipación
  templates/
    shared/                     Base del panel y componentes comunes
    members/                    Pantallas del censo
    activities/                 Pantallas de actividades
    transport/                  Pantallas de transporte
  tests/integration/            Recorridos que cruzan módulos
mobile/
  lib/
    core/                       Acceso, cliente API, navegación y tema
    features/                   Funcionalidades de la app
  test/
  integration_test/
contracts/                      Esquema OpenAPI y ejemplos sintéticos
infra/                          Despliegue, proxy y operación
docs/
  decisions/                    Decisiones técnicas breves
  handoffs/                     Entregas entre agentes cuando sean necesarias
.github/workflows/              Integración continua
```

La estructura se creará al implementar cada funcionalidad, no como un conjunto de carpetas vacías. Si se necesita cambiarla, actualiza este documento y justifica el cambio.

El coordinador asigna un propietario temporal a cada ruta. `backend/config/`, configuración del modelo de usuario, dependencias y archivos de bloqueo, rutas raíz, plantillas compartidas, navegación móvil, esquema OpenAPI global, CI y documentos raíz son archivos de integración: un solo escritor cada vez.

## 4. Reglas del dominio

- Distingue cuenta de acceso y ficha de miembro. Un miembro puede no tener cuenta.
- La identidad de acceso puede ser global; fichas, roles, convocatorias y datos privados pertenecen a una asociación.
- Un usuario puede acumular roles. Los cargos de junta no conceden permisos por sí solos.
- No uses DNI, email o teléfono como clave de negocio universal ni fusiones personas automáticamente por esos campos.
- Distingue convocatoria, respuesta previa y asistencia real. Conserva la trazabilidad de cambios relevantes.
- Guarda fechas en UTC y presenta horarios en la zona de la asociación, teniendo en cuenta cambios de hora.
- Aplica las reglas en servicios de negocio reutilizados por API, panel y tareas. La interfaz móvil no es una barrera de seguridad.
- No calcules pagos a partir de una confirmación de asistencia ni anticipes reglas económicas sin definirlas.

## 5. Aislamiento, privacidad y archivos

Estas condiciones forman parte de la aceptación de cada funcionalidad:

- Toda operación comprueba asociación y permiso en el servidor, incluidos accesos por identificador, relaciones, listados, descargas, tareas y exportaciones.
- Validar el `association_id` enviado por el cliente no basta: debe comprobarse la pertenencia y la coherencia de todas las entidades relacionadas.
- Las restricciones de unicidad de datos locales deben incluir su asociación cuando corresponda.
- Archivos y miniaturas privados no se sirven mediante rutas públicas de medios. Las descargas usan autorización o enlaces temporales tras comprobar permisos.
- Validar fotos por contenido real, tamaño y dimensiones; eliminar metadatos y usar nombres internos. Aplicar los límites descritos en `ANALISIS.md`.
- No registrar DNI, tokens, contraseñas ni datos privados completos en logs o mensajes push.
- No reutilizar una foto privada como imagen pública sin una acción y autorización explícitas.
- No descargar URLs arbitrarias desde importaciones. No ejecutar fórmulas o macros y neutralizar fórmulas en exportaciones.
- Usar datos sintéticos en pruebas y demostraciones.
- No enviar correos o push a personas reales en pruebas; usar adaptadores falsos, buzones de prueba o destinatarios de prueba autorizados.
- No introducir secretos en Git. Los archivos de ejemplo contienen únicamente valores ficticios.

La configuración futura de un sitio público debe exponer una selección explícita de campos. Nunca publiques directamente un serializador privado del censo o de actividades.

## 6. Contratos antes del trabajo paralelo

Antes de desarrollar clientes y servidor en paralelo, el coordinador debe acordar:

1. Modelo de identidad, asociación activa, permisos y autenticación.
2. Identificadores, paginación, errores, formatos de fecha y convenciones de nombres.
3. Estados de actividad, invitación y asistencia, incluidas sus transiciones.
4. Campos públicos y privados y reglas de acceso a fotos.
5. Endpoints del primer recorrido y ejemplos sintéticos de éxito y error.
6. Eventos que generan avisos y datos mínimos que necesitan los trabajadores asíncronos.

Mantén OpenAPI alineado con la implementación. Define un proceso reproducible para generarlo o validarlo al preparar la base. Los agentes propondrán cambios mediante notas o fragmentos de contrato; el propietario del esquema global los integra para evitar sobrescrituras.

Los clientes pueden trabajar con respuestas simuladas que respeten esos contratos. No se considera terminada una función hasta verificarla contra el servidor real de pruebas.

## 7. Organización por subagentes

Se autoriza el trabajo por subagentes para tareas de desarrollo pedidas por el usuario, dentro de su alcance. No conviertas una petición de análisis o documentación en implementación del producto. Solo delega tareas concretas que permitan trabajo independiente útil.

Con cuatro plazas, mantén un coordinador y como máximo tres subagentes activos. Las especialidades siguientes son responsabilidades reutilizables; no requieren siete agentes simultáneos.

| Rol | Propiedad principal | Entregable verificable |
| --- | --- | --- |
| Coordinador / integrador | Arquitectura, contratos globales, archivos compartidos y cambios transversales. | Recorrido integrado, decisiones resueltas y validación completa del alcance pedido. |
| Base y acceso | `accounts`, `associations`, permisos y autenticación. | Dos asociaciones aisladas, acceso funcional y pruebas de autorización. |
| Censo e importación | `members`, fotos y sus pantallas web. | Alta/edición, foto protegida y asistente de importación con informe. |
| Operativa musical | `activities`, `transport` y sus pantallas web. | Crear, convocar, responder, pasar lista y asignar transporte. |
| Cliente móvil | `mobile/`, salvo archivos compartidos asignados a otro propietario. | Recorridos Android/iOS integrados con la API, activación y reactivación de notificaciones y estados de error/carga. |
| Comunicaciones | `communications`, adaptadores de envío y trabajos asíncronos. | Registro y renovación de dispositivos, avisos persistentes, preferencias, reintentos y pruebas con proveedores simulados. |
| Infraestructura y calidad | `infra`, CI y pruebas de integración acordadas. | Entorno reproducible, comprobaciones automáticas y recuperación ensayada. |
| Complemento web, futuro | `website` y sus plantillas públicas. | Publicación explícita con aislamiento entre contenido público y privado. |

Secuencia recomendada:

- Oleada A: base/acceso, esqueleto móvil y entorno/CI. El coordinador cierra los contratos comunes antes de que haya implementaciones divergentes.
- En la oleada A, comprobar pronto permiso y recepción push en dispositivos reales: móvil se ocupa del permiso y configuración nativa; base/acceso, del registro de dispositivo; infraestructura, de la configuración de prueba. Estas piezas se transfieren después a comunicaciones. No posponer la viabilidad de notificaciones a la última oleada.
- Oleada B: censo, operativa y cliente. Censo y operativa incluyen sus vistas web; el agente cliente se concentra en móvil y solo asume pantallas web si se le transfieren rutas expresamente.
- Oleada C: comunicaciones, terminación móvil e integración/calidad. Las pruebas transversales deben usar las APIs acordadas sin cambiar módulos ajenos sin coordinación.
- Oleada D: incidencias del piloto, distribuidas según sus propietarios.
- Complemento web y economía: oleadas posteriores cuando se activen esos alcances.

El coordinador podrá reasignar especialidades entre oleadas. No encargar trabajo dependiente de una decisión sin resolver ni mantener agentes esperando cuando haya tareas independientes disponibles.

### Contrato de una delegación

Cada encargo debe indicar objetivo, rutas permitidas, dependencias, contratos que debe respetar, criterios de aceptación, pruebas relevantes y archivos que no puede tocar. El subagente no ampliará el alcance ni delegará a su vez sin coordinación sobre capacidad y propiedad.

En un árbol de trabajo compartido:

- Un único escritor por archivo o módulo durante cada tarea.
- No sobrescribir cambios ajenos ni ejecutar limpiezas globales, resets o restauraciones destructivas.
- No editar una migración ajena ni regenerar contratos o archivos de bloqueo globales en paralelo.
- Para una necesidad transversal, comunicar el cambio al coordinador y continuar trabajo independiente si es posible.
- Las migraciones tendrán propietario por módulo; el coordinador revisa dependencias y orden antes de integrarlas.
- No ejecutar procesos que compartan y modifiquen la misma base de datos de pruebas sin aislamiento.

La entrega del subagente incluirá archivos modificados, comportamiento final, pruebas ejecutadas y sus resultados, migraciones o configuración necesaria y límites pendientes. El coordinador revisará el código y la integración; un informe de subagente no sustituye la comprobación.

## 8. Pruebas y definición de terminado

Verifica de forma proporcional al riesgo. No añadas pruebas que repitan literalmente la implementación ni ejecutes suites amplias de forma repetida sin cambios que lo justifiquen.

Pruebas prioritarias del MVP:

- Aislamiento de dos asociaciones en consultas, modificaciones, relaciones, fotos, exportaciones y tareas.
- Matriz de permisos y acumulación de roles, incluida una cuenta en dos asociaciones.
- Convocatoria y asistencia independientes; respuestas repetidas o concurrentes coherentes.
- Cambios de horario y cancelación con avisos correctos, sin perder el historial.
- Importación con errores, duplicados y reintentos; previsualización sin altas definitivas e invitaciones solo tras acción explícita.
- Fotos no válidas, límites, permisos de descarga, sustitución y eliminación.
- Capacidad y duplicados en asignación de transporte.
- Caída del proveedor, reintentos y deduplicación de avisos. No prometer entrega exactamente una vez.
- Flujo móvil de acceso, selección de banda, agenda, respuesta y consulta de uniforme/transporte.
- MUST-NOTIF-01 en dispositivos Android e iOS reales: permiso concedido, denegado y posteriormente revocado; reactivación desde ajustes; token renovado; cierre/cambio de cuenta; recepción en primer y segundo plano y apertura de la actividad correcta.
- Distinguir permiso, token registrado y recepción confirmada: ninguno sustituye automáticamente a los otros. No afirmar que la app puede forzar el permiso del sistema ni bloquear todo acceso por denegación sin una decisión de producto expresa.
- Copia y restauración de PostgreSQL y archivos privados.

Una función está terminada cuando tiene servidor e interfaz aplicable integrados, permisos correctos, validación de entradas, estados vacíos/carga/error, textos traducibles, pruebas relevantes superadas y documentación de configuración. No basta una pantalla conectada a datos simulados.

Al crear la base, establecer y documentar en `README.md` los comandos exactos para:

- Instalar dependencias, iniciar servicios y cargar datos sintéticos.
- Ejecutar comprobaciones de Django, migraciones y pruebas backend sobre PostgreSQL.
- Comprobar formato, análisis estático y pruebas Flutter.
- Generar o validar OpenAPI y detectar cambios incompatibles.
- Levantar un entorno de prueba y verificar su salud.

No inventes comandos de scripts todavía inexistentes ni afirmes haber ejecutado pruebas de un componente no creado. Para cambios únicamente documentales, comprueba coherencia, enlaces locales y límites de alcance.

## 9. Gestión del trabajo y comunicación

- Antes de editar, comprueba el estado del repositorio y conserva cambios del usuario.
- Explica las decisiones de alcance que afecten al resultado. Consulta solo cuando falte una decisión material que no pueda inferirse de lo acordado.
- Documenta decisiones técnicas relevantes en `docs/decisions/` cuando aparezcan, con contexto, opción elegida y consecuencias.
- Mantén `ANALISIS.md` alineado si cambia el producto. No reescribas silenciosamente la petición original del README.
- Redacta documentación y comunicaciones del proyecto en castellano; usa identificadores de código en inglés.
- No despliegues a producción, publiques en tiendas, actives gasto o envíes comunicaciones reales sin autorización para esa acción.
- Termina cada tarea con una explicación breve de lo cambiado, su validación y los límites relevantes.
