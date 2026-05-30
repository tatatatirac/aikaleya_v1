from django.urls import path

from telnyx.views.voice import gather_result, inbound_call
from telnyx.views.sms import inbound_sms, sms_status

app_name = "telnyx"

urlpatterns = [
    # Voice (TeXML)
    path("voice/inbound/", inbound_call, name="voice-inbound"),
    path("voice/gather/", gather_result, name="voice-gather"),

    # SMS
    path("sms/webhook/", inbound_sms, name="sms-inbound"),
    path("sms/status/", sms_status, name="sms-status"),
]
