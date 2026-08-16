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

# Bake the bge-m3 weights into the image.
#
# api/apps.py pre-warms the RAG retriever on a daemon thread at startup, and
# sentence-transformers otherwise pulls ~2.3GB from HuggingFace on every cold
# start. Cloud Run's filesystem is ephemeral, so that download repeats for
# every new instance — and because CPU is throttled between requests, it
# crawls, starving the note-analysis worker thread that runs after the POST
# response is sent (observed 2026-08: AI feedback never appeared for new
# notes). Shipping the weights makes pre-warm a local disk read.
#
# Costs ~2.3GB of image size; the Artifact Registry cleanup policy keeps only
# the 2 most recent versions, so storage stays negligible.
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from huggingface_hub import snapshot_download; \
    snapshot_download('BAAI/bge-m3', ignore_patterns=['*.pth', 'onnx/*', '*.onnx', 'imgs/*'])"

# Copy backend code only
COPY backend/ ./backend/

WORKDIR /app/backend

# Collect static files (needs a dummy secret key + dummy Fernet key at build
# time — api.services.encryption.EncryptionService instantiates on module
# import, so collectstatic fails without a valid-shape Fernet key. The real
# ENCRYPTION_KEY is injected by Cloud Run env vars at container start).
RUN DJANGO_SECRET_KEY=build-placeholder \
    ENCRYPTION_KEY=KqdLq5t8ZpDwfyPJ92o6_71UmlWVG8VmPVQgz7OosDo= \
    python manage.py collectstatic --noinput

# Build the ChromaDB RAG index at image-build time.
#
# _get_retriever() auto-bootstraps an empty collection by embedding
# knowledge_base/ with bge-m3, and its docstring assumes min_instances=1 keeps
# that work alive for the revision's lifetime. We run min_instances=0 to keep
# the demo free, so every cold instance re-embedded the same 104 chunks on CPU
# — and the apps.ready() pre-warm thread and the note-analysis worker thread
# raced to do it simultaneously, thrashing both vCPUs so neither finished
# (observed 2026-08: `Embedding 104 chunks with BGE-M3 (device=cpu)` twice in
# the same second, AI feedback never written).
#
# Doing it here costs build time once instead of on every cold start. Keep
# HF_HUB_OFFLINE=1 set at runtime so sentence-transformers reads the baked
# weights instead of re-validating them against huggingface.co.
RUN DJANGO_SECRET_KEY=build-placeholder \
    ENCRYPTION_KEY=KqdLq5t8ZpDwfyPJ92o6_71UmlWVG8VmPVQgz7OosDo= \
    python manage.py load_knowledge_base

# Weights and the Chroma index are baked, so never revalidate against the Hub.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

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
