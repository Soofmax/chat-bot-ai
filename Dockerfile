# Multi-stage build for a minimal, non-root FastAPI image
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser
WORKDIR /app

# Install deps
COPY requirements.txt requirements-dev.txt /app/
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . /app

# Switch to non-root
USER appuser

EXPOSE 8000
ENV ENV=production

# Healthcheck (basic)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]