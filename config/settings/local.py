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
from .base import DEFAULT_AUTO_FIELD
from .base import DEFAULT_FROM_EMAIL
from .base import DJANGO_ADMIN_FORCE_ALLAUTH
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
from .base import LOGGING
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
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="Cfq6xb8MdOGLM68BKIchpYW60jPfB7WU1BRij17zX3vmE90w6jmnibf6pjuSARIP",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]  # noqa: S104

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend",
)

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]


# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ["debug_toolbar"]
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": [
        "debug_toolbar.panels.redirects.RedirectsPanel",
        # Disable profiling panel due to an issue with Python 3.12:
        # https://github.com/jazzband/django-debug-toolbar/issues/1875
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ],
    "SHOW_TEMPLATE_CONTEXT": True,
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]


# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]


# django-cors-headers
# ------------------------------------------------------------------------------
# https://github.com/adamchainz/django-cors-headers
# MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware"] + MIDDLEWARE
# CORS_ALLOW_ALL_ORIGINS = True