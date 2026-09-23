FROM python:3.13-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement /tmp/requirements.txt

COPY backend/ /tmp/backend/
WORKDIR /tmp/backend
RUN python manage.py compilemessages

FROM python:3.13-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /app/var/private_media /app/var/static \
    && chown -R app:app /app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=app:app /tmp/backend/ /app/
COPY --chown=app:app infra/ /app/infra/

USER app
EXPOSE 8000

CMD ["/app/infra/docker/start-web.sh"]
