# syntax=docker/dockerfile:1.7
FROM python:3.13-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencies go in their own stage so application edits do not reinstall them.
# psycopg[binary], bcrypt and cryptography all publish manylinux wheels for
# amd64 and arm64, so no compiler is needed here.
FROM base AS builder
WORKDIR /app
COPY requirements.txt ./
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt

FROM base AS runtime
RUN useradd --system --create-home --uid 10001 app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# alembic.ini uses a relative script_location and prepend_sys_path, both of
# which resolve against the working directory.
WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app

USER app
EXPOSE 8000

# /health returns 503 when the database is unreachable, which raises here and
# marks the container unhealthy rather than quietly serving 500s.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 CMD \
  python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=4).status==200 else 1)"

# --proxy-headers makes request.client.host the real client IP from Caddy's
# X-Forwarded-For, which the login rate limiter keys on. Safe only because port
# 8000 is never published — Caddy is the sole route in.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips=*", \
     "--no-server-header"]
