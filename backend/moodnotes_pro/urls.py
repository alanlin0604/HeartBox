from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    """Liveness/readiness probe for Cloud Run / Docker."""
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'error'}, status=503)


urlpatterns = [
    path('healthz/', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
