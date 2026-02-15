FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies in builder stage
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Runtime stage ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy backend code only
COPY backend/ ./backend/

WORKDIR /app/backend

# Collect static files (needs a dummy secret key at build time)
RUN DJANGO_SECRET_KEY=build-placeholder python manage.py collectstatic --noinput

# Fix ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/healthz/')" || exit 1

# Run migrations then start Daphne (ASGI)
CMD sh -c "python manage.py migrate --noinput && daphne -b 0.0.0.0 -p ${PORT:-8080} moodnotes_pro.asgi:application"
