FROM python:3.11-slim AS base

WORKDIR /app

# Install only production deps
COPY pyproject.toml README.md ./
COPY gauntlet/ gauntlet/

RUN pip install --no-cache-dir ".[all,api]"

# Non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "gauntlet.api:app", "--host", "0.0.0.0", "--port", "8000"]
