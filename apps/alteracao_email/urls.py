from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.alteracao_email.api.views.alteracao_email_viewset import SolicitarAlteracaoEmailViewSet

app_name = "alteracao_email"

router = DefaultRouter()
router.register(r"solicitar", SolicitarAlteracaoEmailViewSet, basename="solicitar_alteracao_email")

urlpatterns = [
    path("", include(router.urls)),
]