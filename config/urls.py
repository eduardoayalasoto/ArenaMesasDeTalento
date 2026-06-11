from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.dashboards.urls")),
    path("cuenta/", include("apps.accounts.urls")),
    path("catalogo/", include("apps.catalog.urls")),
    path("cuestionarios/", include("apps.questionnaires.urls")),
    path("evaluaciones/", include("apps.evaluations.urls")),
]

# Servir archivos subidos (fotos) en desarrollo. En producción usar Blob/S3.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Páginas de error personalizadas en español (se usan cuando DEBUG=False).
handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
