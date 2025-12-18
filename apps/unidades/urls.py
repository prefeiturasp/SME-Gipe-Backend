from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.unidades.api.views.unidades import UnidadeViewSet
from apps.unidades.api.views.gestao_unidade_viewset import GestaoUnidadeViewSet

app_name = "unidades"

router = DefaultRouter()
router.register(r"gestao-unidades", GestaoUnidadeViewSet, basename="gestao-unidades")
router.register(r'', UnidadeViewSet, basename='unidade')


urlpatterns = [
    path("", include(router.urls)),
]