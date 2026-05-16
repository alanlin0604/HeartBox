from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    """Liveness probe — must be ultra-cheap. The frontend pings this on
    every login-page mount to pre-warm Cloud Run, so a DB round-trip
    here adds 50-150 ms to every cold start. Use /readyz/ for DB checks.
    """
    return JsonResponse({'status': 'ok'})


def readiness_check(request):
    """Readiness probe — confirms DB connectivity. Suitable for k8s/Cloud
    Run readiness probes that want to gate traffic on DB availability."""
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'error'}, status=503)


urlpatterns = [
    path('healthz/', health_check, name='health-check'),
    path('readyz/', readiness_check, name='readiness-check'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
