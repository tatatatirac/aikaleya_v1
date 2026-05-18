from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, user_role
from clients.models import BusinessClient, BusinessKnowledgeEntry, ClientApiSettings
from clients.serializers import BusinessClientSerializer, BusinessKnowledgeEntrySerializer, ClientApiSettingsSerializer
from clients.utils import client_for_request


ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svg"}
MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


class BusinessClientViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessClientSerializer
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def get_queryset(self):
        role = user_role(self.request.user)
        if role == "admin":
            return BusinessClient.objects.select_related("owner", "api_settings").all()
        if role == "employee":
            client = client_for_request(self.request)
            if not client:
                return BusinessClient.objects.none()
            return BusinessClient.objects.select_related("owner", "api_settings").filter(id=client.id)
        return BusinessClient.objects.select_related("owner", "api_settings").filter(owner=self.request.user)

    def perform_create(self, serializer):
        owner = self.request.user
        if user_role(self.request.user) == "admin":
            owner = serializer.validated_data.get("owner", self.request.user)
        client = serializer.save(owner=owner)
        ClientApiSettings.objects.get_or_create(business_client=client)

    @action(detail=False, methods=["get", "patch"], url_path="current")
    def current(self, request):
        client = client_for_request(request)
        if client is None:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)

        if request.method == "PATCH":
            if user_role(request.user) == "employee":
                return Response(
                    {"detail": "Zaposleni ne moze da menja podesavanja firme."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            serializer = self.get_serializer(client, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(self.get_serializer(client).data)

    @action(
        detail=False,
        methods=["post", "delete"],
        url_path="logo",
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def logo(self, request):
        """Upload (POST) or remove (DELETE) the business client logo."""
        client = client_for_request(request)
        if client is None:
            return Response({"detail": "Klijent nije pronadjen."}, status=status.HTTP_404_NOT_FOUND)

        if user_role(request.user) == "employee":
            return Response(
                {"detail": "Zaposleni ne moze da menja logo firme."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == "DELETE":
            if client.logo_image:
                client.logo_image.delete(save=False)
            client.logo_image = None
            client.save(update_fields=["logo_image", "updated_at"])
            return Response({"logo_url": None}, status=status.HTTP_200_OK)

        upload = request.FILES.get("logo") or request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "Niste poslali fajl. Polje treba da se zove 'logo'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if upload.size > MAX_LOGO_SIZE_BYTES:
            return Response(
                {"detail": "Fajl je prevelik. Maksimum je 2 MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = (upload.name or "").lower()
        ext = name.rsplit(".", 1)[-1] if "." in name else ""
        if ext not in ALLOWED_LOGO_EXTENSIONS:
            return Response(
                {"detail": "Dozvoljeni formati: PNG, JPG, WebP, SVG."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if client.logo_image:
            client.logo_image.delete(save=False)

        client.logo_image = upload
        client.save()

        serializer = self.get_serializer(client)
        return Response(
            {"logo_url": serializer.data.get("logo_url"), "client": serializer.data},
            status=status.HTTP_200_OK,
        )


class ClientApiSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = ClientApiSettingsSerializer
    permission_classes = (IsAdminRole,)

    def get_queryset(self):
        return ClientApiSettings.objects.select_related("business_client").all()


class BusinessKnowledgeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessKnowledgeEntrySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return BusinessKnowledgeEntry.objects.none()
        return BusinessKnowledgeEntry.objects.filter(business_client=client)

    def _client_for_write(self):
        client = client_for_request(self.request)
        if client is None:
            raise ValidationError({"detail": "Klijent nije pronadjen."})

        role = user_role(self.request.user)
        if role == "employee":
            raise PermissionDenied("Zaposleni ne moze da menja bazu znanja firme.")
        if role != "admin" and client.owner_id != self.request.user.id:
            raise PermissionDenied("Samo vlasnik firme moze da menja bazu znanja.")
        return client

    def perform_create(self, serializer):
        serializer.save(business_client=self._client_for_write())

    def perform_update(self, serializer):
        self._client_for_write()
        serializer.save()

    def perform_destroy(self, instance):
        self._client_for_write()
        instance.delete()
