# Gesband: análisis de producto y plan del MVP

Fecha: 18 de septiembre de 2026.

Estado: propuesta de alcance y arquitectura para iniciar el desarrollo. Este documento no implica que las funciones estén implementadas.

## 1. Objetivo y decisiones

Gesband ayudará a las asociaciones musicales, inicialmente bandas de pueblos de la Comunidad Valenciana, a organizar su actividad y mantener informados a sus miembros. La referencia inicial son asociaciones de hasta 300 miembros; el número total de asociaciones se validará con el piloto.

El objetivo inmediato es comprobar la aceptación del producto: que la junta pueda organizar una actividad con menos trabajo y que los músicos consulten sus convocatorias y respondan desde la aplicación.

Decisiones expresadas por el promotor:

- Priorizar un MVP y validar su aceptación antes de abordar la monetización.
- Desarrollar una solución propia con las tecnologías propuestas; prescindir de Hitobito por ahora.
- Compartir la base de código móvil entre Android e iOS.
- La activación de notificaciones móviles es un requisito MUST del MVP, con flujo guiado, comprobación de estado y validación real en ambas plataformas.
- Alojar el backend y los datos principales en servidores Ubuntu propios.
- Añadir una foto a la ficha del músico.
- Contemplar la gestión de la web de la asociación como un complemento opcional.
- Organizar el desarrollo para permitir trabajo paralelo por subagentes.

La definición concreta del MVP, sus métricas y las fases siguientes son propuestas de trabajo. Las decisiones más recientes del promotor prevalecen sobre este documento y sobre el README original. En particular, no se implementarán ahora los seis meses de prueba, suscripciones, precios ni cortes de acceso por impago.

## 2. Producto y usuarios

Una única plataforma atenderá varias asociaciones, manteniendo separados sus datos y permisos. Habrá una app móvil común y un panel web adaptable para la junta. Al seleccionar una asociación se mostrarán su nombre, logo, colores y lema.

La persona registrada y la cuenta de acceso son conceptos distintos: un socio puede estar dado de alta sin usar la app. Una cuenta puede participar en varias asociaciones; sus funciones y la información visible dependerán de cada una.

| Perfil | Necesidades principales |
| --- | --- |
| Músico | Consultar agenda y convocatorias, confirmar disponibilidad, ver uniforme y transporte, recibir avisos y actualizar los datos permitidos de su ficha. |
| Junta | Mantener miembros, importar datos, planificar actividades, convocar y pasar lista. |
| Contratista u organizador | Preparar actuaciones, conocer disponibilidad y gestionar refuerzos y desplazamientos. |
| Director musical | Preparar ensayos y programas y consultar participación por instrumentos o cuerdas. |
| Tesorería | En una fase posterior, gestionar cuotas y liquidaciones. El cargo se podrá registrar desde el MVP. |
| Socio colaborador o mecenas | Figurar en el censo sin necesitar una cuenta ni participar en convocatorias musicales. |
| Administrador de plataforma | Operar el servicio, dar soporte y gestionar asociaciones con acceso restringido y auditable. |
| Editor web | En el complemento futuro, preparar y publicar contenidos públicos de su asociación. |

Presidencia, vicepresidencia, tesorería, contratista y vocalías serán cargos registrables. Los permisos se concederán mediante roles dentro de cada asociación; no se deducirán automáticamente de una etiqueta de cargo. Una persona podrá acumular varios roles.

## 3. Alcance del MVP

El recorrido que debe quedar completo es:

**Importar miembros → crear actividad → convocar → recibir respuestas → registrar asistencia → revisar resultados.**

### 3.1 Asociación, acceso y permisos

- Alta inicial de asociaciones por el operador del piloto y asignación de administradores.
- Invitación de usuarios, inicio y cierre de sesión y recuperación de acceso.
- Selección de asociación cuando una cuenta participe en varias.
- Configuración de nombre, logo, colores y lema, con límites que mantengan legibilidad.
- Permisos diferenciados para miembros, organizadores, dirección y administración.
- Infraestructura de traducción desde el inicio e interfaces esenciales en castellano y valenciano, con revisión de textos durante el piloto.
- Sin registro comercial, checkout ni cobro por usar Gesband.

### 3.2 Censo y foto del músico

La ficha contemplará nombre, apellidos, DNI/NIE si resulta necesario, dirección, teléfono móvil, email, instrumentos, cuerda, tipo de miembro, estado y foto opcional. No todos los datos deberán ser obligatorios para participar en una convocatoria.

- Separar socios músicos, socios colaboradores y colaboradores musicales externos.
- Permitir registrar un músico externo sin crear una asociación adicional ni darle acceso al censo.
- Permitir varias vinculaciones de una cuenta con asociaciones, sin compartir automáticamente sus fichas privadas.
- Mantener altas y bajas sin destruir el historial de participación.
- No usar DNI, email o teléfono como identificador técnico de la persona.
- No exigir email único entre fichas: puede ser compartido por familiares. La identidad de acceso tendrá sus propias reglas de unicidad y verificación.
- Permitir al músico editar su foto y los datos de contacto autorizados; la junta gestionará instrumentos, pertenencia y cargos.

La foto será privada por defecto y visible únicamente para la propia persona y los roles autorizados que la necesiten, por ejemplo para pasar lista. No habrá un directorio fotográfico abierto para todos los socios por defecto.

Propuesta técnica para fotos: aceptar JPEG, PNG y WebP, hasta 5 MB; comprobar el contenido real, limitar dimensiones y píxeles decodificados, corregir orientación, eliminar metadatos y generar una miniatura. Usar nombres internos aleatorios y acceso autenticado. Permitir sustituir y eliminar la imagen. La foto privada nunca se publicará automáticamente en la web de la asociación.

Si el piloto incluye menores, resolver antes de incorporarlos las relaciones con tutores, el acceso y la autorización de uso de imágenes. No asumir un correo o dispositivo independiente para cada menor.

### 3.3 Importación inicial

Asistente de carga CSV y XLSX con este recorrido:

1. Descargar una plantilla con ejemplos e instrucciones.
2. Subir el fichero y asociar sus columnas a los campos del censo.
3. Validar formatos, valores y posibles duplicados.
4. Mostrar una previsualización de altas, actualizaciones, advertencias y rechazos.
5. Confirmar los cambios y obtener un informe por fila.
6. Enviar invitaciones en una acción independiente, elegida por la junta.

No se fusionarán personas automáticamente por coincidencia de nombre, email o teléfono. Las actualizaciones usarán identificadores estables de la asociación o una selección explícita. Repetir una importación deberá detectar registros ya tratados y evitar altas duplicadas. La previsualización no escribirá fichas definitivas.

En el MVP las fotos se subirán desde cada ficha; la carga masiva de fotos queda fuera. El importador no descargará imágenes desde URLs incluidas en una hoja de cálculo. Se limitarán tamaño y filas, no se ejecutarán fórmulas o macros y se neutralizarán fórmulas peligrosas en exportaciones para hojas de cálculo.

### 3.4 Ensayos, actuaciones y convocatorias

- Calendario y listado de actividades con tipos ensayo y actuación.
- Fecha, horario, lugar, hora de concentración, descripción, uniforme y estado de publicación.
- Duplicación de actividades para agilizar ensayos habituales; recurrencias complejas quedan aplazadas.
- Selección de destinatarios por personas, instrumentos o cuerdas, con previsualización.
- Convocatoria individual con estados pendiente, aceptada y rechazada; respuesta hasta una fecha límite configurable.
- Asistencia real separada de la respuesta previa: sin registrar, presente, ausente o ausencia justificada.
- Resumen de confirmaciones y asistencias por instrumento o cuerda.
- Modificación y cancelación con aviso a las personas afectadas.
- Cambios relevantes de fecha o lugar podrán requerir una nueva confirmación; se conservará el historial de respuestas.
- Programa o repertorio básico mediante una lista ordenada de títulos y notas. La biblioteca de partituras queda aplazada.

La junta y el director tendrán vistas de grupo según sus permisos. Cada músico verá sus convocatorias y respuestas; no recibirá por defecto información personal completa de los demás.

### 3.5 Transporte básico

Para una actuación se podrá indicar un medio de transporte, punto y hora de salida, conductor cuando corresponda, plazas y personas asignadas. El músico verá su asignación.

Se comprobarán plazas disponibles y asignaciones duplicadas. No se implementarán optimización de rutas, seguimiento GPS ni cálculo de compensaciones en esta fase.

### 3.6 Comunicaciones

- Bandeja persistente de avisos dentro de la app.
- Notificaciones push para convocatorias, recordatorios, cambios y cancelaciones. Su activación guiada y verificable es obligatoria en el alcance del MVP y no se podrá aplazar para después del piloto.
- Correo con la misma información operativa, también cuando las notificaciones push no estén disponibles. El correo no sustituye el requisito de implementar y validar push.
- Enlaces que abran la actividad correspondiente después de autenticar y comprobar permisos.
- Preferencias de recordatorios para evitar comunicaciones innecesarias, sin ocultar el estado de activación de notificaciones del dispositivo.
- Registro de intentos de envío, errores y estados que realmente comunique el proveedor.

Requisito **MUST-NOTIF-01: activación de notificaciones móviles**:

1. Incluir durante la incorporación del usuario un paso visible que explique para qué se necesitan los avisos y solicite el permiso del sistema.
2. Comprobar por separado el permiso concedido, el registro del dispositivo en el backend y el resultado de una prueba de recepción. Tener un token push no demuestra que el usuario pueda ver avisos.
3. Si se deniega el permiso o está desactivado, mantener visible el paso pendiente, explicar la consecuencia y ofrecer acceso a los ajustes del sistema cuando corresponda. No repetir indefinidamente una solicitud que el sistema ya no pueda mostrar.
4. Volver a comprobar el estado al regresar a la app, especialmente desde ajustes, y mostrar un aviso de reactivación cuando se detecte la desactivación.
5. Gestionar renovación de tokens, cambios de cuenta y cierre de sesión para evitar avisos dirigidos a una persona en la sesión de otra.
6. Verificar en Android e iOS reales la recepción con permiso concedido, el comportamiento en primer y segundo plano y la apertura de la convocatoria correcta al pulsar el aviso.

El permiso final pertenece al usuario y al sistema operativo: Gesband no puede activarlo unilateralmente ni garantizar la entrega de cada aviso. El MUST exige que este recorrido funcione y se valide antes del piloto. No establece por sí solo un bloqueo de acceso a toda la app cuando se deniega el permiso; una restricción de ese tipo requeriría una decisión de producto explícita. Las autorizaciones provisionales o silenciosas se mostrarán como tales, sin confundirlas con avisos plenamente habilitados.

El MVP propondrá compartir mensajes preparados por WhatsApp con individuos o grupos mediante la función de compartir del móvil o copiar el mensaje desde la web. El usuario elegirá el destinatario y confirmará el envío en WhatsApp. Gesband no podrá asegurar entrega o lectura de estos mensajes.

Esta solución asistida no satisface un eventual requisito de envío automático a grupos grandes. La integración automática individual con WhatsApp Business y cualquier automatización de grupos quedan pendientes de validar capacidades, condiciones y costes. No se usarán automatizaciones no oficiales de WhatsApp Web.

### 3.7 Encuestas a los miembros

Añadido el 23 de septiembre de 2026 a petición del promotor.

La junta necesita consultar a la banda —fechas de un viaje, compra de material,
uniforme nuevo— sin recurrir a un grupo de WhatsApp donde cada voto queda a la
vista de todos y quien responde tarde ya sabe lo que han dicho los demás.

- La junta crea una encuesta con un enunciado, sus opciones y un plazo de
  votación. Mientras no se abra permanece en borrador y se puede corregir.
- Los destinatarios se eligen como los de una convocatoria: por personas,
  instrumentos o cuerdas. La encuesta se anuncia por los mismos canales que una
  convocatoria y aparece en la bandeja de avisos.
- **Cada persona vota una sola vez.** El servidor rechaza el segundo intento;
  no basta con ocultar el botón en el cliente.
- **El voto es anónimo.** El sistema debe poder demostrar que alguien ya votó
  sin poder decir qué votó. Esto obliga a separar el registro de participación
  —quién ha votado— de las papeletas, sin ninguna clave que las relacione. Una
  columna `votante` en la tabla de votos incumple el requisito aunque nadie la
  consulte.
- Mientras el plazo sigue abierto, quien puede votar ve el **recuento provisional
  anónimo**: totales por opción, nunca quién eligió qué.
- Al vencer el plazo se cierra la votación y la junta **publica el resultado
  definitivo**. La publicación es una acción explícita, no un efecto automático
  del reloj: permite revisar la participación antes de dar por bueno el recuento.
- El resultado publicado queda consultable después, con la fecha de cierre y el
  número de votos emitidos sobre el de convocados.

Decisiones que quedan abiertas y no impiden documentar el requisito:

- Tipos de pregunta admitidos. La propuesta mínima es opción única; opción
  múltiple y orden de preferencia se evaluarán al implementarla.
- Si la junta puede ver el recuento provisional cuando los miembros no, o si
  ambos ven lo mismo mientras está abierta.
- Si una encuesta puede anularse una vez abierta y qué se conserva si se anula.
- Si el plazo vencido sin publicar oculta también el provisional.

El anonimato tiene una consecuencia que conviene aceptar por escrito: una vez
emitido, un voto no se puede modificar ni retirar a petición de quien lo emitió,
porque el sistema no sabe cuál es suyo.

## 4. Fuera del MVP, sin perderlos del producto

| Función | Tratamiento previsto |
| --- | --- |
| Cuotas de socios, donaciones y recibos | Siguiente fase funcional tras validar el uso operativo. |
| Liquidaciones por actuación y coche | Definir reglas reales con las bandas antes de automatizar cálculos. |
| Ejecución de pagos, remesas y conciliación bancaria | Proyecto posterior; registrar importes no equivale a mover dinero. |
| Suscripciones de Gesband, precios y prueba de seis meses | Aplazados hasta validar aceptación. |
| Web pública de la asociación | Complemento opcional especificado en la sección 5. |
| Biblioteca de partituras y documentos musicales | Posterior, con permisos de acceso y publicación definidos. |
| Búsqueda de refuerzos entre asociaciones | Posterior; el MVP solo registra colaboradores invitados por cada banda. |
| Edición completa sin conexión | Posterior; inicialmente consulta limitada de información sincronizada. |
| Chat propio, red social o apps independientes por banda | Sin prioridad para la validación inicial. |

La tesorería de las asociaciones y la monetización de Gesband son ámbitos distintos. La primera se aplaza para concentrar el piloto, no porque dependa de activar suscripciones comerciales.

## 5. Complemento: web de la asociación

La plataforma contemplará un módulo opcional para gestionar una web pública desde el panel. Se especifica ahora y se reservarán sus límites arquitectónicos; no será un requisito para lanzar el MVP operativo ni se construirá un CMS completo anticipadamente.

Primera versión propuesta del complemento:

- Portada con identidad visual de la asociación.
- Páginas institucionales: presentación, historia, contacto y junta, si se desea publicar.
- Noticias y agenda pública de actuaciones.
- Imágenes públicas seleccionadas expresamente para publicación.
- Navegación, metadatos básicos para buscadores y diseño adaptable.
- Borrador, previsualización, publicación y retirada de contenidos.
- Rol editor web independiente del permiso de administrar socios.
- Subdominio inicial; dominio propio en una ampliación según demanda.

Se propone renderizar las páginas públicas con plantillas Django para facilitar indexación y reutilizar el servidor. El editor inicial usaría formularios estructurados y contenido saneado, sin permitir scripts o HTML arbitrario. La necesidad de un CMS especializado se evaluará cuando se aborde el complemento.

La activación se hará por asociación mediante configuración funcional, sin vincularla ahora a un plan de pago. No exige una plataforma genérica de plugins.

Reglas de publicación:

- Las fichas de músicos, fotos privadas, DNIs, contactos personales, respuestas, asistencias, transportes y datos económicos no serán contenido público.
- Publicar una actuación será una acción explícita que seleccione únicamente los datos públicos, como título, lugar y horario de actuación.
- La publicación mantendrá un vínculo con la actividad original y una regla explícita para actualizar o retirar cambios y cancelaciones, sin sincronizar campos privados.
- Las imágenes públicas se almacenarán y servirán separadas de las privadas, con autorización de publicación registrada cuando corresponda.
- Desactivar el complemento retirará el acceso público sin afectar a la gestión interna de la asociación.

## 6. Arquitectura y tecnologías

| Componente | Tecnología y enfoque |
| --- | --- |
| Android e iOS | Flutter y Dart; una app común, organizada por funcionalidades. |
| API y lógica | Django y Django REST Framework. |
| Persistencia | PostgreSQL. |
| Panel de la junta | Vistas y formularios propios con plantillas Django y mejora progresiva; HTMX solo donde simplifique una interacción concreta. |
| Operación interna | Django Admin restringido al personal autorizado, con controles de acceso por asociación. |
| Procesamiento asíncrono | Celery y RabbitMQ para comunicaciones e importaciones. |
| Push | Firebase Cloud Messaging; en iOS también interviene APNs. |
| Correo | Proveedor SMTP transaccional configurable; seleccionar el proveedor al preparar el piloto. |
| Archivos | Almacenamiento privado mediante la abstracción de Django; volumen persistente inicial, migrable a almacenamiento compatible con S3. |
| Despliegue | Docker Compose sobre Ubuntu y proxy inverso con HTTPS. |
| Web pública opcional | Módulo Django con plantillas públicas y permisos editoriales propios. |

Se utilizará una aplicación de servidor modular. No se introducirán microservicios ni Kubernetes para el piloto. Se fijarán versiones soportadas de las dependencias y sus archivos de bloqueo al crear la base del proyecto.

Flujo general:

```text
App Flutter ───── API /api/v1/ ──┐
Panel web de la junta ──────────┼── Django ── PostgreSQL
Web pública opcional ──────────┘      │
                                     ├── Archivos privados / públicos separados
                                     └── Trabajos persistentes → Celery / RabbitMQ
                                                                ├── Correo
                                                                └── FCM / APNs
```

La app y el panel compartirán servicios de negocio y permisos; no se duplicarán reglas en cada interfaz. La base de datos del dominio permanecerá en los servidores propios, pero correo y push implican proveedores externos.

Para iOS se necesitarán macOS y Xcode, propios o mediante CI, además de la preparación de la publicación. El servidor Ubuntu no sustituye ese entorno de compilación.

### 6.1 Aislamiento y acceso

- Base de datos compartida con identificación de asociación en las entidades de negocio.
- La asociación activa se resolverá en el servidor comprobando la pertenencia del usuario; no se confiará en un identificador recibido del cliente.
- Consultas, relaciones, restricciones de unicidad, archivos, cachés, exportaciones y tareas asíncronas respetarán el mismo aislamiento.
- Un identificador válido de otra asociación no permitirá leer ni modificar sus registros.
- Autenticación web mediante sesiones seguras y protección CSRF. Para móvil, credenciales revocables y renovación mediante una solución mantenida, elegida y documentada antes de implementar acceso; no crear criptografía propia.
- La ficha local de una persona no se expondrá a otra banda porque ambas compartan una cuenta de acceso.

### 6.2 API y fiabilidad

- API versionada, paginada y descrita con OpenAPI: permisos, campos, errores y ejemplos sintéticos.
- Identificadores estables, fechas almacenadas en UTC y presentadas según la zona de la asociación, inicialmente Europe/Madrid.
- Contrato explícito de estados de convocatoria y asistencia.
- Creación de avisos asociada a la transacción de negocio mediante una bandeja persistente de salida o mecanismo equivalente recuperable.
- Reintentos con límites y deduplicación por actividad, versión, destinatario y canal. No prometer entrega exactamente una vez cuando el proveedor no la garantice.
- Una caída del proveedor de correo o push no hará desaparecer una actividad confirmada ni su aviso interno.
- Cambios concurrentes y confirmaciones repetidas se resolverán mediante restricciones y transacciones del servidor.

### 6.3 Consulta sin cobertura

La app podrá conservar la última agenda y las convocatorias propias, indicando cuándo se sincronizaron. La información almacenada será mínima: no se guardará localmente un censo con DNI, direcciones o fotos de terceros.

No se presentará una respuesta como enviada mientras no exista confirmación del servidor. Los datos locales de una asociación se eliminarán al cerrar sesión o al detectar la revocación de acceso. La política de caducidad de caché debe reconocer que una revocación no puede comprobarse mientras el dispositivo permanezca sin conexión.

## 7. Modelo de datos inicial

Los nombres son orientativos hasta cerrar el contrato y las primeras migraciones.

| Entidad | Responsabilidad |
| --- | --- |
| Account | Identidad de acceso global, sin convertir el censo completo en un directorio compartido. |
| Association | Configuración, zona horaria e identidad visual. |
| Member | Ficha local de socio o colaborador, foto privada y vínculo opcional con Account. |
| AssociationRole | Permisos de una cuenta dentro de una asociación; admite acumulación de roles. |
| Instrument / Section | Catálogo de instrumentos y agrupaciones musicales. |
| MemberInstrument | Instrumentos de un miembro y designación principal. |
| Activity | Ensayo o actuación, horarios, lugar, uniforme y estado. |
| ProgrammeItem | Títulos y notas ordenados dentro de una actividad. |
| Invitation | Destinatario, respuesta, plazos e historial relevante. |
| Attendance | Asistencia real, autor del registro y modificaciones auditables. |
| Transport / TransportAssignment | Medio, plazas y asignación por actividad. |
| ImportBatch | Fichero temporal, previsualización, confirmación e informe de importación. |
| Notification / Delivery | Aviso persistente y seguimiento por canal. |
| DeviceRegistration | Dispositivo y token push vinculados a una cuenta, con revocación. |
| AuditEntry | Cambios relevantes y accesos administrativos excepcionales, sin copiar secretos o datos completos. |

El complemento futuro añadirá configuración de sitio, páginas, noticias y publicaciones de actividades. La tesorería futura añadirá cuotas y liquidaciones. No se crearán todavía tablas comerciales o financieras vacías por anticipación.

## 8. Privacidad, seguridad y operación

- Minimizar los campos obligatorios y determinar con las bandas para qué necesitan DNI y dirección.
- Proteger tanto archivos originales como miniaturas y evitar URLs públicas para fotos privadas.
- Mantener una distinción explícita entre foto de ficha y autorización para publicación web.
- No incluir DNIs, credenciales ni datos privados completos en logs, push o mensajes compartidos.
- Usar datos sintéticos en desarrollo, pruebas, capturas y documentación.
- Limitar intentos de acceso y validar ficheros, formularios y contenido editorial.
- Definir conservación de importaciones, fotos sustituidas, datos de bajas, auditoría y copias antes del piloto con datos reales.
- Copias cifradas fuera del servidor principal y ensayo de restauración de base de datos y archivos.
- Separar entornos, gestionar secretos fuera del repositorio y monitorizar errores, trabajos pendientes, espacio y copias.
- Documentar responsabilidades sobre datos, proveedores y uso de imágenes al incorporar cada asociación; los textos definitivos deberán ajustarse al funcionamiento real del servicio.

La política comercial de caducidad queda aplazada. Las bajas de personas y las solicitudes de supresión seguirán necesitando un procedimiento durante el piloto.

## 9. Validación de aceptación

Propuesta inicial: piloto con dos asociaciones durante seis a ocho semanas, incluyendo personas de junta, dirección y músicos con distintos niveles de familiaridad tecnológica. No es el periodo comercial de seis meses descrito originalmente.

Las métricas son hipótesis para acordar al iniciar el piloto, no resultados ni garantías:

| Señal | Medición propuesta |
| --- | --- |
| Activación | Al menos el 60 % de músicos invitados activa su acceso durante las primeras dos semanas. Denominador: músicos invitados, no todo el censo. |
| Activación de notificaciones | Medir por plataforma cuántas instalaciones con sesión tienen permiso concedido y registro push vigente; registrar por separado las pruebas de recepción confirmadas. No confundir activación de cuenta con activación de avisos. |
| Uso de convocatorias | Al menos el 70 % de convocados con cuenta activa responde dentro del plazo, medido sobre las últimas tres actividades. |
| Adopción por la junta | Cada banda completa al menos tres actividades reales con convocatoria y asistencia registradas. |
| Utilidad | Comparar el tiempo dedicado antes y durante el piloto y recoger ejemplos concretos de trabajo evitado o añadido. |
| Continuidad | Ambas juntas quieren seguir utilizándolo y pueden identificar qué mejorar antes de ampliarlo. |
| Calidad | Sin defectos conocidos de aislamiento o pérdida de datos; errores de envío visibles y recuperables. |

Recoger el motivo de no uso, no solo clics: dificultades de acceso, notificaciones desactivadas, falta de cobertura, duplicación de trabajo o preferencia por WhatsApp. No incorporar seguimiento individual invasivo para medir aceptación.

Al finalizar se decidirá entre corregir el MVP, ampliarlo funcionalmente o explorar monetización. La petición de un complemento web se medirá por separado para no confundirla con la utilidad de la gestión de bandas.

## 10. Fases y condiciones de salida

| Fase | Entregables | Condición de salida |
| --- | --- | --- |
| 0. Definición | Recorridos, prototipo de pantallas, permisos, datos de ejemplo y decisiones abiertas. | Una banda puede recorrer un ensayo y una actuación completos en el prototipo. |
| 1. Base compartida | Repositorio, entorno, modelo de asociación/cuenta, autenticación, API inicial, CI y prueba temprana del permiso y recepción push en Android/iOS. | Alta de dos asociaciones sintéticas, pruebas efectivas de aislamiento y viabilidad del flujo push comprobada en dispositivos reales. |
| 2. MVP funcional | Censo y fotos, importación, agenda, convocatorias, asistencia, transporte básico y comunicaciones. | Recorrido completo desde importación hasta asistencia en web y móvil. |
| 3. Preparación del piloto | Pruebas en dispositivos, despliegue de pruebas, restauración, guías y corrección de incidencias. | MUST-NOTIF-01 verificado en Android/iOS; responsables de las bandas pueden operar y el servicio puede recuperarse de una copia. |
| 4. Piloto | Uso real, soporte y medición durante seis a ocho semanas propuestas. | Decisión documentada sobre continuidad y siguientes prioridades. |
| 5. Ampliaciones | Tesorería, complemento web, automatizaciones o monetización según evidencia. | Alcance específico validado antes de cada ampliación. |

No se fija una fecha de entrega sin conocer dedicación y equipo. Las dependencias de publicación móvil y la revisión de las bandas deben incluirse al estimar.

## 11. Trabajo por subagentes

El reparto detallado y sus reglas están en `AGENTS.md`. Los roles son paquetes de responsabilidad, no agentes que deban ejecutarse todos a la vez.

Con cuatro plazas de ejecución se propone un coordinador y hasta tres subagentes simultáneos:

| Oleada | Trabajo paralelo | Dependencia |
| --- | --- | --- |
| A | Modelo y acceso; base móvil con datos sintéticos; entorno y CI. Prueba temprana coordinada de permiso y recepción push. | Contrato inicial acordado por el coordinador. |
| B | Censo/fotos/importación con sus pantallas web; actividades/asistencia/transporte con sus pantallas web; cliente móvil. | Modelo de asociación, autenticación y contratos mínimos estables. |
| C | Comunicaciones; terminación del cliente móvil; integración, seguridad y pruebas de recorridos. | Eventos de negocio y API de las funcionalidades disponibles. |
| D | Correcciones del piloto repartidas por módulo. | Evidencia de uso e incidencias reproducibles. |
| Futuro | Complemento web y módulos económicos, en tareas separadas. | Decisión posterior al piloto o ampliación expresa del alcance. |

Cada oleada se adapta a las dependencias reales: no se mantienen agentes ocupados en tareas bloqueadas. El coordinador integra cambios transversales y valida el producto completo.

## 12. Decisiones pendientes que no impiden documentar ni crear la base

- Asociaciones piloto y persona de referencia de cada una.
- Reglas de acceso de menores y tutores, si los hay.
- Campos personales que realmente se necesitan y quién puede modificarlos.
- Política exacta de visibilidad de listados y asistencia para cada rol.
- Canal y frecuencia de recordatorios; proveedor de correo del piloto.
- Acceso al entorno macOS, cuentas de distribución y dispositivos de prueba.
- Si el complemento web se pide para el piloto; por defecto permanece fuera del MVP.
- Si compartir manualmente por WhatsApp cubre el piloto; automatizar grupos requiere una validación distinta.

Las decisiones sobre pagos a músicos, cuotas, precios y suscripciones se retomarán al abordar esos módulos.

## 13. Antecedentes y referencias

El análisis previo consideró Hitobito, Admidio, Galette y CiviCRM como posibles bases libres. Se conserva ese antecedente, pero por decisión del promotor no se instalará ni adaptará Hitobito en esta etapa. Se reutilizarán bibliotecas y herramientas mantenidas, con revisión de sus licencias.

Referencias consultadas en el análisis inicial; las condiciones de terceros deben comprobarse de nuevo al integrar cada servicio:

- [Flutter: desarrollo multiplataforma](https://flutter.dev/development).
- [Flutter: compilación y publicación en iOS](https://docs.flutter.dev/deployment/ios).
- [Django](https://docs.djangoproject.com/en/6.0/) y [Django REST Framework](https://www.django-rest-framework.org/).
- [Firebase Cloud Messaging para Flutter](https://firebase.google.com/docs/cloud-messaging/flutter/get-started).
- [Política de WhatsApp Business](https://business.whatsapp.com/policy).
- [Integración de grupos de WhatsApp de Bird](https://bird.com/docs/guides/whatsapp/groups). Es documentación del proveedor; no se ha validado directamente la documentación técnica de Meta sobre grupos.
- [Protección de datos desde el diseño, AEPD](https://www.aepd.es/derechos-y-deberes/cumple-tus-deberes/medidas-de-cumplimiento/proteccion-de-datos-desde-el-diseno).
- [Hitobito](https://github.com/hitobito/hitobito) y [extensión para asociaciones musicales suizas](https://github.com/hitobito/hitobito_sbv).
- [Admidio](https://github.com/Admidio/admidio), [Galette](https://doc.galette.eu/en/master/usermanual/index.html) y [CiviCRM](https://docs.civicrm.org/user/en/latest/introduction/what-is-civicrm/).
