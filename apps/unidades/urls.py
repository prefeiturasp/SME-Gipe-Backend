from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.unidades.api.views.unidades import UnidadeViewSet

app_name = "unidades"

router = DefaultRouter()
router.register(r'', UnidadeViewSet, basename='unidade')

urlpatterns = [
    path("", include(router.urls)),
]