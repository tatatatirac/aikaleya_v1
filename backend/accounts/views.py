import os

from django.contrib.auth import login as django_login, logout as django_logout
from django.core.management import call_command
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import ClientRegistrationSerializer, LoginSerializer, UserSerializer
from accounts.throttles import AuthRateThrottle
from clients.serializers import BusinessClientSerializer
from clients.utils import client_for_request


class LoginAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        django_login(request._request, user)
        token, _created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class MeAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class RegisterClientAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    def post(self, request):
        serializer = ClientRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        user = result["user"]
        token, _created = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
                "client": BusinessClientSerializer(result["client"]).data,
                "trial_days": result["plan"].trial_days,
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        demo_client_email = os.environ.get("KALEYA_DEMO_CLIENT_EMAIL", "administrator@test.com").strip().lower()
        demo_employee_email = os.environ.get("KALEYA_DEMO_EMPLOYEE_EMAIL", "employee@test.com").strip().lower()
        demo_employee_username = os.environ.get("KALEYA_DEMO_EMPLOYEE_USERNAME", "employee").strip().lower()
        user_email = (request.user.email or "").strip().lower()
        username = (request.user.username or "").strip().lower()
        if user_email in {demo_client_email, demo_employee_email} or username == demo_employee_username:
            call_command("seed_demo", verbosity=0)
        Token.objects.filter(user=request.user).delete()
        django_logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GdprExportAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        profile = getattr(user, "profile", None)

        data = {
            "exported_at": timezone.now().isoformat(),
            "user": {
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_joined": user.date_joined.isoformat(),
            },
            "profile": {
                "role": profile.role if profile else None,
                "phone": profile.phone if profile else None,
                "created_at": profile.created_at.isoformat() if profile else None,
            },
        }

        client = client_for_request(request)
        if client:
            data["business"] = {
                "name": client.name,
                "business_type": getattr(client, "business_type", None),
                "language": getattr(client, "language", None),
                "timezone": getattr(client, "timezone", None),
            }
            from appointments.models import Appointment
            appointments = (
                Appointment.objects.filter(business_client=client)
                .select_related("customer", "service")
                .order_by("-date", "-start_time")[:500]
            )
            data["appointments"] = [
                {
                    "date": str(a.date),
                    "start_time": str(a.start_time),
                    "status": a.status,
                    "service": a.service.name if a.service else a.title,
                    "customer": a.customer.full_name if a.customer else None,
                    "channel": a.channel,
                    "notes": a.notes,
                    "created_at": a.created_at.isoformat(),
                }
                for a in appointments
            ]

        response = JsonResponse(data, json_dumps_params={"ensure_ascii": False, "indent": 2})
        response["Content-Disposition"] = 'attachment; filename="kaleya-data-export.json"'
        return response


class GdprDeleteAccountAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user = request.user
        demo_emails = {
            os.environ.get("KALEYA_DEMO_CLIENT_EMAIL", "administrator@test.com").strip().lower(),
            os.environ.get("KALEYA_DEMO_ADMIN_EMAIL", "admin@aikaleya.com").strip().lower(),
        }
        if (user.email or "").strip().lower() in demo_emails or user.is_superuser:
            return Response({"detail": "Demo i superuser nalozi ne mogu biti obrisani."}, status=status.HTTP_403_FORBIDDEN)

        profile = getattr(user, "profile", None)
        if profile and profile.deletion_scheduled_at:
            return Response({
                "detail": "Nalog je vec zakazan za brisanje.",
                "deletion_scheduled_at": profile.deletion_scheduled_at.isoformat(),
            })

        scheduled_at = timezone.now() + timedelta(days=30)
        user.is_active = False
        user.save(update_fields=["is_active"])
        if profile:
            profile.deletion_scheduled_at = scheduled_at
            profile.save(update_fields=["deletion_scheduled_at", "updated_at"])

        Token.objects.filter(user=user).delete()
        django_logout(request._request)

        return Response({
            "detail": "Nalog je deaktiviran. Bice trajno obrisan za 30 dana.",
            "deletion_scheduled_at": scheduled_at.isoformat(),
        })


class GdprCancelDeleteAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    def post(self, request):
        from django.contrib.auth.models import User as AuthUser
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        if not email or not password:
            return Response({"detail": "Email i lozinka su obavezni."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = AuthUser.objects.get(email__iexact=email, is_active=False)
        except AuthUser.DoesNotExist:
            return Response({"detail": "Nalog nije pronadjen ili je vec aktivan."}, status=status.HTTP_404_NOT_FOUND)

        if not user.check_password(password):
            return Response({"detail": "Pogresna lozinka."}, status=status.HTTP_403_FORBIDDEN)

        profile = getattr(user, "profile", None)
        if not profile or not profile.deletion_scheduled_at:
            return Response({"detail": "Ovaj nalog nije zakazan za brisanje."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save(update_fields=["is_active"])
        profile.deletion_scheduled_at = None
        profile.save(update_fields=["deletion_scheduled_at", "updated_at"])

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"detail": "Brisanje naloga je otkazano. Dobrodosli nazad.", "token": token.key})
