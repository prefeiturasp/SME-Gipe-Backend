from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponseRedirect
from django.test import RequestFactory
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.users.models import User
from apps.users.views import UserRedirectView, UserUpdateView, user_detail_view

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    
    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):

        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user
        view.request = request

        assert view.get_success_url() == f"/users/{user.username}/"

    def test_get_object(self, user: User, rf: RequestFactory):

        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user
        view.request = request

        assert view.get_object() == user

    def test_post_valid_data(self, client, user: User):

        client.force_login(user)
        url = reverse("users:update")
        response = client.post(url, {"name": "Novo Nome"})
        user.refresh_from_db()

        assert response.status_code == HTTPStatus.FOUND
        assert user.name == "Novo Nome"

    def test_post_invalid_data(self, client, user: User):

        client.force_login(user)
        url = reverse("users:update")
        response = client.post(url, {"name": ""})

        assert response.status_code == HTTPStatus.OK
        assert "name" in response.context["form"].errors

    def test_success_message(self, client, user: User):

        client.force_login(user)
        url = reverse("users:update")
        response = client.post(url, {"name": "Teste Mensagem"}, follow=True)
        messages_list = list(response.context["messages"])

        assert any(_("Information successfully updated") == m.message for m in messages_list)


class TestUserRedirectView:

    def test_get_redirect_url(self, user: User, rf: RequestFactory):

        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user
        view.request = request

        assert view.get_redirect_url() == f"/users/{user.username}/"


class TestUserDetailView:

    def test_authenticated(self, user: User, rf: RequestFactory):

        request = rf.get("/fake-url/")
        request.user = user
        response = user_detail_view(request, username=user.username)

        assert response.status_code == HTTPStatus.OK

    def test_not_authenticated(self, user: User, rf: RequestFactory):

        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request, username=user.username)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"{login_url}?next=/fake-url/"