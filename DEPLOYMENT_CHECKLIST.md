# MoodNotes Pro Deployment Checklist

## 1. Backend Environment Variables
Set these in your hosting platform:

- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY=<secure-random>`
- `DJANGO_ALLOWED_HOSTS=<api-domain>`
- `DATABASE_URL=<postgres-url>`
- `CORS_ALLOWED_ORIGINS=<frontend-domain>`
- `CSRF_TRUSTED_ORIGINS=<frontend-domain>`
- `ENCRYPTION_KEY=<fernet-key>`
- `OPENAI_API_KEY=<optional>`
- `FRONTEND_URL=<frontend-domain>`
- `DEFAULT_FROM_EMAIL=<noreply address>`
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST=<smtp-host>`
- `EMAIL_PORT=587`
- `EMAIL_HOST_USER=<smtp-user>`
- `EMAIL_HOST_PASSWORD=<smtp-password>`
- `EMAIL_USE_TLS=True`
- `THROTTLE_LOGIN=10/hour`
- `THROTTLE_REGISTER=5/hour`
- `THROTTLE_PASSWORD_RESET=5/hour`

## 2. Database Migration
Run in backend:

```bash
python manage.py migrate
```

## 3. Static & Media
- Ensure `collectstatic` runs during build (`backend/build.sh` already does this).
- Ensure persistent storage for `media/` if you need avatars/attachments retention.

## 4. Frontend Environment Variables
Set in frontend host (if not using proxy):

- `VITE_API_URL=https://<api-domain>/api`
- `VITE_WS_URL=wss://<api-domain>`

## 5. Post-deploy Smoke Checks
- Login/register works with remember-me on/off.
- Password reset email arrives and reset link works.
- Avatar upload displays in top nav/chat/counselor list.
- Logout other devices invalidates previous sessions.
- Notifications and chat WebSocket connect over `wss://`.
- PWA install prompt appears on supported browsers.
