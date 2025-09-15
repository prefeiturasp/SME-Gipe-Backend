from auditlog.registry import auditlog
from django.contrib.auth import get_user_model

User = get_user_model()

auditlog.register(
    User,
    exclude_fields=['last_login'],
)