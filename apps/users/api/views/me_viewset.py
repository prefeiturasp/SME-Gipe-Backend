from django.db.models import Prefetch
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from apps.users.api.serializers.me_serializer import UserMeSerializer

User = get_user_model()

class MeView(APIView):
    """
    Retorna os dados do usuário autenticado (requer Bearer access token).
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):

        username = getattr(request.user, "username", None)
        if not username:
            return Response({"detail": "Não autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

        qs = (
            User.objects
            .select_related("cargo")
            .prefetch_related(
                Prefetch("unidades", to_attr="unidades_cache"),
                "unidades__dre"
            )
        )

        try:
            user = qs.get(pk=request.user.pk)

        except User.DoesNotExist:
            return Response({"detail": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserMeSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)