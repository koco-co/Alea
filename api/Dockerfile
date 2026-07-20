FROM ghcr.io/astral-sh/uv:0.11.28 AS uv
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
RUN apt-get update && apt-get install --no-install-recommends -y curl && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY app ./app
RUN addgroup --system alea && adduser --system --ingroup alea alea && chown -R alea:alea /app
USER alea
EXPOSE 8000
CMD ["uv", "run", "--locked", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
