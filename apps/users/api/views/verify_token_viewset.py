from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authentication import get_authorization_header
from rest_framework_simplejwt.serializers import TokenVerifySerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class VerifyTokenFlexibleView(APIView):
    """
    Verifica o token de acesso.
    Aceita:
      - POST body: {"token": "<ACCESS_TOKEN>"}
      - Header: Authorization: Bearer <ACCESS_TOKEN>
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):

        token = self._extract_token(request)
        if not token:
            return Response(
                {"detail": "Token ausente. Envie no body (token) ou no header Authorization: Bearer <token>."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TokenVerifySerializer(data={"token": token})
        try:
            serializer.is_valid(raise_exception=True)

        except (InvalidToken, TokenError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({"detail": "Token válido.", "status": status.HTTP_200_OK})

    @staticmethod
    def _extract_token(request) -> str | None:

        token = request.data.get("token")
        if token:
            return token
        
        auth = get_authorization_header(request).split()
        if auth and auth[0].lower() == b"bearer" and len(auth) == 2:
            try:
                return auth[1].decode("utf-8")
            
            except Exception:
                return None
        return None