from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from accounts.permissions import user_role
from ai_agent.models import AIIntent, AIToolRun, CustomerMemory
from ai_agent.providers import ProviderError, _post_json, get_client_ai_config, get_client_voice_config, synthesize_elevenlabs_speech
from ai_agent.serializers import (
    AIIntentSerializer,
    AIToolRunSerializer,
    CustomerMemorySerializer,
    InboundTextSerializer,
    TextToSpeechSerializer,
)
from ai_agent.services import handle_inbound_text
from appointments.models import Customer
from billing.services import enforce_channel_allowed, enforce_elevenlabs_voice_allowed
from clients.utils import client_for_request
from communications.models import Conversation


PUBLIC_INTRO_TEXT = {
    "sr": "Zdravo, ja sam Kaleya, AI sekretarica koja odgovara na pozive, zakazuje termine i obavestava vas tim.",
    "en": "Hello, I am Kaleya, an AI receptionist that answers calls, schedules appointments and alerts your team.",
    "es": "Hola, soy Kaleya, una recepcionista de IA que atiende llamadas, agenda citas y avisa a tu equipo.",
    "pt": "Ola, eu sou Kaleya, uma recepcionista de IA que atende chamadas, agenda horarios e avisa sua equipe.",
    "ru": "Здравствуйте, я Kaleya, AI администратор, который отвечает на звонки, записывает клиентов и уведомляет команду.",
    "fr": "Bonjour, je suis Kaleya, une receptionniste IA qui repond aux appels, planifie les rendez-vous et informe votre equipe.",
    "it": "Ciao, sono Kaleya, una receptionist AI che risponde alle chiamate, organizza appuntamenti e avvisa il tuo team.",
    "de": "Hallo, ich bin Kaleya, ein AI Empfang, der Anrufe beantwortet, Termine plant und Ihr Team benachrichtigt.",
}

PUBLIC_CLIENT_GREETING_TEXT = {
    "sr": "Izvolite, ovde Kaleya. Kako mogu da pomognem?",
    "en": "Hello, this is Kaleya. How can I help?",
    "es": "Hola, soy Kaleya. Como puedo ayudar?",
    "pt": "Ola, aqui e Kaleya. Como posso ajudar?",
    "ru": "Здравствуйте, это Kaleya. Чем могу помочь?",
    "fr": "Bonjour, ici Kaleya. Comment puis-je aider ?",
    "it": "Ciao, sono Kaleya. Come posso aiutare?",
    "de": "Hallo, hier ist Kaleya. Wie kann ich helfen?",
}

PUBLIC_VOICE_PRESETS = {
    "intro": PUBLIC_INTRO_TEXT,
    "client_greeting": PUBLIC_CLIENT_GREETING_TEXT,
}


class PublicVoiceClient:
    id = "public"


class AIIntentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AIIntentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return AIIntent.objects.none()
        return AIIntent.objects.select_related("conversation", "customer").filter(business_client=client)


class AIToolRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AIToolRunSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return AIToolRun.objects.none()
        return AIToolRun.objects.select_related("intent").filter(business_client=client)


class CustomerMemoryViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerMemorySerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        role = user_role(self.request.user)
        queryset = CustomerMemory.objects.select_related(
            "business_client",
            "customer",
            "last_service",
            "preferred_staff_member",
        )

        if role == "admin":
            client_id = self.request.query_params.get("client_id")
            if client_id:
                queryset = queryset.filter(business_client_id=client_id)
            return queryset

        if role == "employee":
            return CustomerMemory.objects.none()

        client = client_for_request(self.request)
        if not client:
            return CustomerMemory.objects.none()
        return queryset.filter(business_client=client)

    def perform_update(self, serializer):
        memory = self.get_object()
        role = user_role(self.request.user)
        if role == "employee":
            raise PermissionDenied("Zaposleni ne moze da menja memoriju musterija.")
        if role != "admin" and memory.business_client.owner_id != self.request.user.id:
            raise PermissionDenied("Samo vlasnik firme moze da menja memoriju musterija.")
        serializer.save()


class InboundTextAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = InboundTextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        enforce_channel_allowed(client, serializer.validated_data.get("channel", "web"))
        is_demo = bool(getattr(client, "is_demo", False))

        conversation = None
        customer = None
        if serializer.validated_data.get("conversation_id"):
            conversation = Conversation.objects.filter(
                id=serializer.validated_data["conversation_id"],
                business_client=client,
            ).first()
        if serializer.validated_data.get("customer_id"):
            customer = Customer.objects.filter(
                id=serializer.validated_data["customer_id"],
                business_client=client,
            ).first()

        result = handle_inbound_text(
            client,
            serializer.validated_data["text"],
            conversation=conversation,
            customer=customer,
            channel=serializer.validated_data.get("channel", "web"),
            payload={
                key: serializer.validated_data.get(key)
                for key in (
                    "customer_name",
                    "phone",
                    "email",
                    "appointment_id",
                    "customer_id",
                    "service_id",
                    "service_hint",
                    "staff_member_id",
                    "staff_hint",
                    "date",
                    "time",
                    "duration_minutes",
                    "title",
                    "reason",
                    "cancelled_reason",
                )
                if key in serializer.validated_data
            },
            use_ai=False if is_demo else serializer.validated_data.get("use_ai", True),
            include_voice=False if is_demo else serializer.validated_data.get("include_voice", False),
            external_thread_id=serializer.validated_data.get("external_thread_id", ""),
            actor=request.user,
            is_test=bool(serializer.validated_data.get("is_private_test", False)),
        )
        if is_demo:
            result["demo_mode"] = True
            result["ai_provider"] = "demo-fallback"
            result["voice"] = None
        return Response(result)


class TextToSpeechAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = TextToSpeechSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        if getattr(client, "is_demo", False):
            return Response(
                {"detail": "Demo nalog ne koristi stvarni ElevenLabs TTS."},
                status=403,
            )
        enforce_elevenlabs_voice_allowed(client)

        try:
            return Response(synthesize_elevenlabs_speech(client, serializer.validated_data["text"]))
        except ProviderError as exc:
            return Response({"detail": str(exc)}, status=400)


class PublicIntroSpeechAPIView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        preset = (request.query_params.get("preset") or "intro").strip().lower()
        preset_texts = PUBLIC_VOICE_PRESETS.get(preset)
        if preset_texts is None:
            return Response({"detail": "Nepoznat voice preset."}, status=404)

        language = (request.query_params.get("lang") or "en").strip().lower()
        if language not in preset_texts:
            language = "en"
        text = preset_texts[language]

        try:
            voice = synthesize_elevenlabs_speech(PublicVoiceClient(), text, language=language)
            return Response({"preset": preset, "language": language, "text": text, **voice})
        except ProviderError as exc:
            return Response({"detail": str(exc), "preset": preset, "language": language}, status=400)


class VoiceStatusAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        if getattr(client, "is_demo", False):
            return Response(
                {
                    "provider": "elevenlabs",
                    "connected": False,
                    "package_allows_voice": False,
                    "api_key_set": False,
                    "voice_id_set": False,
                    "model_id": "",
                    "demo_mode": True,
                }
            )

        config = get_client_voice_config(client)
        api_key_set = bool(config.get("api_key"))
        voice_id_set = bool(config.get("voice_id"))
        package_allows_voice = False
        try:
            enforce_elevenlabs_voice_allowed(client)
            package_allows_voice = True
        except Exception:
            package_allows_voice = False
        return Response(
            {
                "provider": "elevenlabs",
                "connected": package_allows_voice and api_key_set and voice_id_set,
                "package_allows_voice": package_allows_voice,
                "api_key_set": api_key_set,
                "voice_id_set": voice_id_set,
                "model_id": config.get("model_id", ""),
            }
        )


class PublicChatThrottle(AnonRateThrottle):
    scope = 'public_browser_chat'

    def _client_ip(self, request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def allow_request(self, request, view):
        # IP whitelist (skip throttle for owner / staff testing IPs).
        # Configure via PUBLIC_CHAT_THROTTLE_WHITELIST=ip1,ip2,ip3 in .env.
        from django.conf import settings as dj_settings
        whitelist = getattr(dj_settings, "KALEYA_PUBLIC_CHAT_THROTTLE_WHITELIST", "") or ""
        whitelist_ips = {ip.strip() for ip in whitelist.split(",") if ip.strip()}
        client_ip = self._client_ip(request)
        if client_ip and client_ip in whitelist_ips:
            return True
        return super().allow_request(request, view)


class PublicBrowserChatAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (PublicChatThrottle,)

    # Legacy stub — actual demo prompt is built per-request via master_prompt.py
    _DEMO_PROMPT = ""

    def post(self, request):
        text = (request.data.get("text") or "").strip()[:500]
        lang = (request.data.get("lang") or "en").strip().lower()[:5]
        history = request.data.get("history") or []

        if not text:
            return Response({"detail": "Text is required."}, status=400)

        messages = []
        for item in list(history)[-6:]:
            role = (item.get("role") or "").strip()
            content = (item.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": text})

        reply_text = ""
        try:
            from ai_agent.master_prompt import build_demo_master_prompt
            config = get_client_ai_config(PublicVoiceClient())
            if not config.get("api_key"):
                raise ProviderError("AI not configured.")
            response = _post_json(
                "https://api.anthropic.com/v1/messages",
                {
                    "model": config["model"],
                    "max_tokens": 200,
                    "temperature": 0.65,
                    "system": build_demo_master_prompt(language=lang),
                    "messages": messages,
                },
                {
                    "Content-Type": "application/json",
                    "x-api-key": config["api_key"],
                    "anthropic-version": "2023-06-01",
                },
            )
            blocks = [b.get("text", "") for b in (response.get("content") or []) if b.get("type") == "text"]
            reply_text = "\n".join(b for b in blocks if b).strip()
        except ProviderError:
            fallback = {
                "en": "Hello, this is Kaleya! How can I help you today?",
                "sr": "Zdravo, ovde Kaleya! Kako mogu da pomognem?",
                "es": "Hola, soy Kaleya. ¿En qué le puedo ayudar?",
                "fr": "Bonjour, ici Kaleya. Comment puis-je vous aider?",
                "de": "Hallo, hier ist Kaleya. Wie kann ich Ihnen helfen?",
                "it": "Ciao, sono Kaleya. Come posso aiutarla?",
                "pt": "Olá, aqui é Kaleya. Como posso ajudar?",
                "ru": "Здравствуйте, это Kaleya. Чем могу помочь?",
            }
            reply_text = fallback.get(lang, fallback["en"])

        result = {"text": reply_text, "audio_url": None}
        try:
            voice = synthesize_elevenlabs_speech(PublicVoiceClient(), reply_text, language=lang)
            result["audio_url"] = voice.get("audio_url")
        except ProviderError:
            pass

        return Response(result)


class ProviderStatusAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        if getattr(client, "is_demo", False):
            return Response(
                {
                    "ai": {"provider": "demo", "model": "keyword-fallback", "connected": False},
                    "voice": {
                        "provider": "elevenlabs",
                        "model_id": "",
                        "connected": False,
                        "package_allows_voice": False,
                    },
                    "demo_mode": True,
                }
            )

        ai_config = get_client_ai_config(client)
        voice_config = get_client_voice_config(client)
        package_allows_voice = False
        try:
            enforce_elevenlabs_voice_allowed(client)
            package_allows_voice = True
        except Exception:
            package_allows_voice = False
        return Response(
            {
                "ai": {
                    "provider": ai_config.get("provider", ""),
                    "model": ai_config.get("model", ""),
                    "connected": bool(ai_config.get("api_key")),
                },
                "voice": {
                    "provider": voice_config.get("provider", "elevenlabs"),
                    "model_id": voice_config.get("model_id", ""),
                    "connected": package_allows_voice and bool(voice_config.get("api_key")) and bool(voice_config.get("voice_id")),
                    "package_allows_voice": package_allows_voice,
                },
            }
        )
