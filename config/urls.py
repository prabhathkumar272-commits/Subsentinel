"""
Root URL configuration for the SubSentinel project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("subscriptions/", include("apps.subscriptions.urls", namespace="subscriptions")),
    path("imports/", include("apps.imports.urls", namespace="imports")),
    path("insights/", include("apps.insights.urls", namespace="insights")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("", include("apps.core.urls", namespace="core")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ---------------------------------------------------------------------------
# Custom error handlers
# ---------------------------------------------------------------------------
handler400 = "apps.core.views.handler400"
handler403 = "apps.core.views.handler403"
handler404 = "apps.core.views.handler404"
handler500 = "apps.core.views.handler500"

# ---------------------------------------------------------------------------
# Admin site customization
# ---------------------------------------------------------------------------
admin.site.site_header = "SubSentinel Administration"
admin.site.site_title = "SubSentinel Admin"
admin.site.index_title = "Dashboard"
