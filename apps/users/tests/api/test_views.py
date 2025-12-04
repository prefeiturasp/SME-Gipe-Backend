import pytest
from rest_framework.test import APIRequestFactory

from apps.users.api.view import UserViewSet
from apps.users.models import User


class TestUserViewSet:
    @pytest.fixture
    def api_rf(self) -> APIRequestFactory:
        return APIRequestFactory()

    def test_get_queryset(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/", secure=True)
        request.user = user

        view.request = request

        assert user in view.get_queryset()

    def test_me(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/", secure=True)
        request.user = user

        view.request = request

        response = view.me(request)  # type: ignore[call-arg, arg-type, misc]

        expected_data = {
            "username": user.username,
            "url": f"https://testserver/api/users/{user.username}/",
            "name": user.name,
        }

        assert response.data == expected_data