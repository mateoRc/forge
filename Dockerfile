FROM python:3.13-slim AS base

ARG VERSION=dev
LABEL org.opencontainers.image.title="Forge" \
      org.opencontainers.image.version="${VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FORGE_VERSION="${VERSION}"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir --requirement requirements-dev.txt

COPY app app
COPY scripts scripts
COPY tests tests
RUN python -m pytest

FROM base AS runtime

RUN useradd --create-home forge \
    && mkdir --parents /app/data \
    && chown forge:forge /app/data
COPY --from=test --chown=forge:forge /app/app app
COPY --from=test --chown=forge:forge /app/scripts scripts

USER forge
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
