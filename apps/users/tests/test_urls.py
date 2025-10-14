from django.urls import resolve
from django.urls import reverse

from apps.users.models import User


def test_detail(user: User):
    assert (
        reverse("users:detail", kwargs={"username": user.username})
        == f"/api/users/{user.username}/"
    )
    assert resolve(f"/api/users/{user.username}/").view_name == "users:detail"


def test_update():
    assert reverse("users:update") == "/api/users/~update/"
    assert resolve("/api/users/~update/").view_name == "users:update"


def test_redirect():
    assert reverse("users:redirect") == "/api/users/~redirect/"
    assert resolve("/api/users/~redirect/").view_name == "users:redirect"


def test_login():
    assert reverse("users:login") == "/api/users/login"
    assert resolve("/api/users/login").view_name == "users:login"


def test_password_reset():
    assert reverse("users:esqueci-senha") == "/api/users/esqueci-senha"
    assert resolve("/api/users/esqueci-senha").view_name == "users:esqueci-senha"