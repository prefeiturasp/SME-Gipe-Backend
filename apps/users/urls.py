# apps/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view

from apps.users.api.views.me_viewset import MeView
from apps.users.api.views.login_viewset import LoginView
from apps.users.api.views.verify_token_viewset import VerifyTokenFlexibleView
from apps.users.api.views.usuario_viewset import UserCreateView
from apps.users.api.views.senha_viewset import (
    EsqueciMinhaSenhaViewSet,
    RedefinirSenhaViewSet,
    AtualizarSenhaViewSet,
)
from apps.users.api.views.gestao_usuario_viewset import GestaoUsuarioViewSet
from apps.users.api.views.intercorrencia_viewset import IntercorrenciaViewSet

app_name = "users"

router = DefaultRouter()
router.register(r"gestao-usuarios", GestaoUsuarioViewSet, basename="usuarios-gestao")
router.register(r"intercorrencias", IntercorrenciaViewSet, basename="intercorrencias")

urlpatterns = [
    
        # Rotas da API de gestão de usuarios (ViewSet)
    path("", include(router.urls)),
    
    # Rotas "antigas" / site / auxiliares
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),

    # Autenticação & fluxo público
    path("login", view=LoginView.as_view(), name="login"),
    path("esqueci-senha", view=EsqueciMinhaSenhaViewSet.as_view(), name="esqueci-senha"),
    path("registrar", view=UserCreateView.as_view(), name="registrar"),  # cadastro público rede indireta
    path("redefinir-senha", view=RedefinirSenhaViewSet.as_view(), name="redefinir-senha"),
    path("atualizar-senha", view=AtualizarSenhaViewSet.as_view(), name="atualizar-senha"),
    path("me", MeView.as_view(), name="me"),
    path("verify-token", VerifyTokenFlexibleView.as_view(), name="verify-token"),
]
