"""
With these settings, tests run faster.
"""

# ruff: noqa: E501
from .base import ACCOUNT_ADAPTER
from .base import ACCOUNT_ALLOW_REGISTRATION
from .base import ACCOUNT_EMAIL_VERIFICATION
from .base import ACCOUNT_FORMS
from .base import ACCOUNT_LOGIN_METHODS
from .base import ACCOUNT_SIGNUP_FIELDS
from .base import ADMIN_URL
from .base import ADMINS
from .base import APPS_DIR
from .base import AUTH_PASSWORD_VALIDATORS
from .base import AUTH_USER_MODEL
from .base import AUTHENTICATION_BACKENDS
from .base import BASE_DIR
from .base import CORS_URLS_REGEX
from .base import CRISPY_ALLOWED_TEMPLATE_PACKS
from .base import CRISPY_TEMPLATE_PACK
from .base import CSRF_COOKIE_HTTPONLY
from .base import DATABASES
from .base import DEBUG
from .base import DEFAULT_AUTO_FIELD
from .base import DEFAULT_FROM_EMAIL
from .base import DJANGO_ADMIN_FORCE_ALLAUTH
from .base import EMAIL_BACKEND
from .base import EMAIL_HOST
from .base import EMAIL_HOST_PASSWORD
from .base import EMAIL_HOST_USER
from .base import EMAIL_PORT
from .base import EMAIL_TIMEOUT
from .base import EMAIL_USE_TLS
from .base import FIXTURE_DIRS
from .base import FORM_RENDERER
from .base import INSTALLED_APPS
from .base import LANGUAGE_CODE
from .base import LOCALE_PATHS
from .base import LOGIN_REDIRECT_URL
from .base import LOGIN_URL
from .base import MANAGERS
from .base import MEDIA_ROOT
from .base import MEDIA_URL
from .base import MIDDLEWARE
from .base import MIGRATION_MODULES
from .base import PASSWORD_HASHERS
from .base import PASSWORD_RESET_TIMEOUT
from .base import REDIS_SSL
from .base import REDIS_URL
from .base import REST_FRAMEWORK
from .base import ROOT_URLCONF
from .base import SESSION_COOKIE_HTTPONLY
from .base import SIMPLE_JWT
from .base import SITE_ID
from .base import SOCIALACCOUNT_ADAPTER
from .base import SOCIALACCOUNT_FORMS
from .base import SPECTACULAR_SETTINGS
from .base import STATIC_ROOT
from .base import STATIC_URL
from .base import STATICFILES_DIRS
from .base import STATICFILES_FINDERS
from .base import TEMPLATES
from .base import TIME_ZONE
from .base import USE_I18N
from .base import USE_TZ
from .base import WSGI_APPLICATION
from .base import X_FRAME_OPTIONS
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="ewsvaSYiuO8qha7iNcma2Py3NtiNsPBNrFfAk1mFcGMcyE9fBI4wJ12iPSDLolxF",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DEBUGGING FOR TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore[index]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "http://media.testserver/"
# Your stuff...
# ------------------------------------------------------------------------------
