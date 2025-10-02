from django.urls import path

from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view

from apps.users.api.views.me_viewset import MeView
from apps.users.api.views.login_viewset import LoginView
from apps.users.api.views.verify_token_viewset import VerifyTokenFlexibleView
from apps.users.api.views.usuario_viewset import UserCreateView, UserUpdateView
from apps.users.api.views.senha_viewset import EsqueciMinhaSenhaViewSet, RedefinirSenhaViewSet, AtualizarSenhaViewSet

app_name = "users"

urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),
    path("login", view=LoginView.as_view(), name="login"),
    path('esqueci-senha', view=EsqueciMinhaSenhaViewSet.as_view(), name="esqueci-senha"),
    path("registrar", view=UserCreateView.as_view(), name="registrar"),
    path('redefinir-senha', view=RedefinirSenhaViewSet.as_view(), name="redefinir-senha"),
    path('atualizar-senha', view=AtualizarSenhaViewSet.as_view(), name="atualizar-senha"),
    path("atualizar-dados", view=UserUpdateView.as_view(), name="atualizar-dados"),
    path("me", MeView.as_view(), name="me"),
    path("verify-token", VerifyTokenFlexibleView.as_view(), name="verify-token")
]