# Infraestructura de Gesband

Esta carpeta contiene un entorno reproducible para desarrollo y ensayo del MVP. No despliega producción ni activa proveedores reales. PostgreSQL y RabbitMQ solo son accesibles desde la red de Compose; Caddy publica el puerto HTTP de desarrollo.

## Inicio local

Requisitos: Docker Engine con el complemento Compose y un backend existente en `backend/` con `requirements.txt` y `manage.py`.

```bash
cp infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/compose.yaml config --quiet
docker compose --env-file infra/.env -f infra/compose.yaml up --build -d
docker compose --env-file infra/.env -f infra/compose.yaml ps
```

El proxy queda en `http://localhost:8080`. Su sonda es `/proxy-health`; Django debe implementar `/health/` sin revelar datos internos. `start-web.sh` aplica migraciones y recopila estáticos antes de iniciar Gunicorn. En despliegues con más de una réplica, las migraciones deberán pasar a una tarea única anterior al arranque.

Los valores de `.env.example` son intencionadamente ficticios. Antes de cualquier entorno compartido hay que cambiar contraseñas y clave de Django, desactivar `DJANGO_DEBUG`, limitar hosts y orígenes, y usar el gestor de secretos del entorno.

## HTTPS

`caddy/Caddyfile.dev` sirve HTTP local. `caddy/Caddyfile.https.example` es la base para un servidor con DNS público: requiere `DOMAIN` y `ACME_EMAIL`, y Caddy debe publicar 80/443 con volúmenes persistentes. Es un ejemplo revisable, no un despliegue automático. No se debe habilitar HSTS hasta confirmar que el dominio funciona exclusivamente por HTTPS.

## Copias y restauración

La copia incluye un volcado lógico de PostgreSQL, los archivos privados y sus checksums. RabbitMQ no se copia: los avisos pendientes deben persistir en PostgreSQL y poder reencolarse; la cola no es la fuente de verdad.

```bash
infra/scripts/backup.sh
infra/scripts/verify-backup.sh infra/backups/gesband-FECHA.tar.gz
infra/scripts/restore.sh infra/backups/gesband-FECHA.tar.gz --confirm-replace
```

`backup.sh` exige PostgreSQL en ejecución. `verify-backup.sh` comprueba checksums, que el archivo de medios se puede leer y que `pg_restore` reconoce el volcado. La restauración detiene web, worker y proxy, reemplaza base y medios, reinicia servicios y ejecuta `manage.py check --deploy`.

Antes del piloto se debe ensayar la restauración en un proyecto Compose aislado, verificar una muestra de fichas y fotos sintéticas, y registrar duración y resultado. Las copias reales deberán cifrarse y almacenarse fuera del servidor principal con una política de retención acordada; estos scripts generan el paquete local que alimentará ese proceso.

## Diagnóstico

```bash
docker compose --env-file infra/.env -f infra/compose.yaml ps
docker compose --env-file infra/.env -f infra/compose.yaml logs --tail=200 web worker proxy
docker compose --env-file infra/.env -f infra/compose.yaml exec web python manage.py check
```

Los adaptadores locales usan correo por consola y proveedor push falso. No introduzcas credenciales FCM/APNs o SMTP en `.env.example`, imágenes ni Git.

