# Pinned by digest so the build is reproducible; bump quarterly via
# scripts/bump-base-image.ps1 (sha picked from docker hub). The bare
# `python:3.12-slim` tag drifts and can introduce unrelated CVEs
# between builds.
FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Pull in any security patches the pinned base hasn't merged yet.
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies in builder stage
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Runtime stage ---
# Pinned by digest so the build is reproducible; bump quarterly via
# scripts/bump-base-image.ps1 (sha picked from docker hub). The bare
# `python:3.12-slim` tag drifts and can introduce unrelated CVEs
# between builds.
FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

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

# Health check removed - Cloud Run uses its own health checking mechanism
# HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
#     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/healthz/')" || exit 1

# Run migrations (retry for transient Neon Postgres connection timeouts) then start Daphne (ASGI).
# Without retry, a single migrate failure exits before daphne binds to $PORT, which Cloud Run
# surfaces as the cryptic "Container import failed" via startupProbe timeout.
CMD sh -c "for i in 1 2 3; do python manage.py migrate --noinput && break || echo 'Migration attempt $i failed, retrying in 5s...' && sleep 5; done && daphne -b 0.0.0.0 -p ${PORT:-8080} moodnotes_pro.asgi:application"
