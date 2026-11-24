from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import SimpleRouter

from mock_sso import views as mock_sso_views

admin.site.site_header = admin.site.site_title = "UniPlace"
admin.site.index_title = "Administração"

router = SimpleRouter()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# O Mock IdP só existe no modo mock: com o SSO real (SSO_ADAPTER=oidc) a rota nem é publicada.
if settings.SSO_ADAPTER == "mock":
    urlpatterns.append(path("mock-sso/authorize/", mock_sso_views.authorize))

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # só ativo com DEBUG=True
