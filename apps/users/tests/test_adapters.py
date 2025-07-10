import pytest
from unittest import mock
from django.conf import settings

from apps.users.adapters import AccountAdapter, SocialAccountAdapter
from apps.users.models import User


class TestAccountAdapter:
    @pytest.mark.parametrize("allow_registration", [True, False])
    def test_is_open_for_signup(self, settings, allow_registration):
        settings.ACCOUNT_ALLOW_REGISTRATION = allow_registration
        adapter = AccountAdapter()
        result = adapter.is_open_for_signup(request=mock.Mock())
        assert result is allow_registration


class TestSocialAccountAdapter:
    @pytest.mark.parametrize("allow_registration", [True, False])
    def test_is_open_for_signup(self, settings, allow_registration):
        settings.ACCOUNT_ALLOW_REGISTRATION = allow_registration
        adapter = SocialAccountAdapter()
        result = adapter.is_open_for_signup(
            request=mock.Mock(),
            sociallogin=mock.Mock()
        )
        assert result is allow_registration

    @pytest.mark.django_db
    def test_populate_user_with_name(self):
        adapter = SocialAccountAdapter()
        data = {"name": "Nome Completo"}
        user_instance = User()

        with mock.patch(
            "apps.users.adapters.DefaultSocialAccountAdapter.populate_user",
            return_value=user_instance
        ):
            user = adapter.populate_user(
                request=mock.Mock(),
                sociallogin=mock.Mock(),
                data=data
            )

        assert user.name == "Nome Completo"

    @pytest.mark.django_db
    def test_populate_user_with_first_and_last_name(self):
        adapter = SocialAccountAdapter()
        data = {"first_name": "Nome", "last_name": "Sobrenome"}
        user_instance = User()

        with mock.patch(
            "apps.users.adapters.DefaultSocialAccountAdapter.populate_user",
            return_value=user_instance
        ):
            user = adapter.populate_user(
                request=mock.Mock(),
                sociallogin=mock.Mock(),
                data=data
            )

        assert user.name == "Nome Sobrenome"

    @pytest.mark.django_db
    def test_populate_user_with_first_name_only(self):
        adapter = SocialAccountAdapter()
        data = {"first_name": "Nome"}
        user_instance = User()

        with mock.patch(
            "apps.users.adapters.DefaultSocialAccountAdapter.populate_user",
            return_value=user_instance
        ):
            user = adapter.populate_user(
                request=mock.Mock(),
                sociallogin=mock.Mock(),
                data=data
            )

        assert user.name == "Nome"

    @pytest.mark.django_db
    def test_populate_user_with_existing_name(self):
        adapter = SocialAccountAdapter()
        data = {}
        social_user = User(name="Já Existente")

        with mock.patch(
            "apps.users.adapters.DefaultSocialAccountAdapter.populate_user",
            return_value=social_user
        ):
            user = adapter.populate_user(
                request=mock.Mock(),
                sociallogin=mock.Mock(),
                data=data
            )

        assert user.name == "Já Existente"