# --- Build / runtime image for the FastAPI backend (Phase 22) ----------------
# Multi-stage to keep the runtime image lean. We pin Python 3.11 because that
# matches what every test we've shipped runs against.

FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: libpq-dev/libmariadb only when we need a sync MySQL driver, but
# pymysql + aiomysql are both pure-Python so we get away with a minimal set.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential libssl-dev libffi-dev libjpeg-dev zlib1g-dev curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Final stage --------------------------------------------------------------
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    UPLOAD_DIR=/app/uploads

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libjpeg62-turbo zlib1g curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 1001 --home /app appuser

# Copy the venv-equivalent (system site-packages from the base stage) over.
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

WORKDIR ${APP_HOME}
COPY --chown=appuser:appuser . ${APP_HOME}

# Storage volume for per-tenant uploads (mounted from a host disk in prod).
RUN mkdir -p ${UPLOAD_DIR} && chown -R appuser:appuser ${UPLOAD_DIR}

USER appuser
EXPOSE 8000

# uvicorn with sensible defaults; override workers in compose if needed.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
