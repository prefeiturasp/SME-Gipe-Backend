from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import BasePermission

from apps.unidades.services.carga_unidade_service import CargaUnidadeService


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


class CargaUnidadeViewSet(ViewSet):

    authentication_classes = [BasicAuthentication]
    permission_classes = [IsSuperUser]

    def _file(self, request):
        file = request.FILES.get("file")
        if not file:
            return None, Response({"erro": "Arquivo não enviado"}, status=400)
        return file, None

    def _response(self, result):
        if not result.get("success"):
            return Response(result, status=400)

        return Response(result.get("data", result))

    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        file, error = self._file(request)
        if error:
            return error

        result = CargaUnidadeService.preview(file)
        return self._response(result)

    @action(detail=False, methods=["post"], url_path="confirm")
    def confirm(self, request):
        file, error = self._file(request)
        if error:
            return error

        result = CargaUnidadeService.confirm(file)
        return self._response(result)