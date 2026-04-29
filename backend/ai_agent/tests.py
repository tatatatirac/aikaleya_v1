from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase

from ai_agent.services import handle_inbound_text
from appointments.models import Appointment
from billing.models import Plan
from clients.models import BusinessClient


class AIAppointmentToolTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="client@example.com", email="client@example.com", password="test12345")
        self.client = BusinessClient.objects.create(
            owner=self.user,
            name="AI Test Business",
            package=Plan.CODE_PRO,
            interface_language="en",
            language="en",
            work_start=time(9, 0),
            work_end=time(16, 0),
            slot_interval_minutes=30,
        )

    def test_ai_can_check_availability_without_external_provider(self):
        result = handle_inbound_text(
            self.client,
            "Check free slots today",
            channel="web",
            payload={"date": date.today()},
            use_ai=False,
        )

        self.assertEqual(result["intent"], "check_availability")
        self.assertEqual(result["tool_output"]["free_count"], 14)
        self.assertEqual(result["ai_provider"], "fallback")

    def test_ai_can_book_structured_appointment_without_external_provider(self):
        result = handle_inbound_text(
            self.client,
            "Book appointment",
            channel="web",
            payload={
                "date": date.today(),
                "time": time(10, 0),
                "customer_name": "Emily Carter",
                "phone": "+15550101",
            },
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "booked")
        self.assertEqual(Appointment.objects.count(), 1)
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.customer.full_name, "Emily Carter")
        self.assertEqual(appointment.start_time, time(10, 0))

