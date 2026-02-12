FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code only
COPY backend/ ./backend/

WORKDIR /app/backend

# Collect static files (needs a dummy secret key at build time)
RUN DJANGO_SECRET_KEY=build-placeholder python manage.py collectstatic --noinput

EXPOSE 8080

# Run migrations then start Daphne (ASGI)
CMD sh -c "python manage.py migrate --noinput && daphne -b 0.0.0.0 -p ${PORT:-8080} moodnotes_pro.asgi:application"
