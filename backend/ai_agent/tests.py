from datetime import date, time
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from ai_agent.services import handle_inbound_text
from appointments.models import Appointment
from billing.models import Plan
from clients.models import BusinessClient
from staff_services.models import StaffMember


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

    @mock.patch("ai_agent.services.generate_anthropic_reply", return_value="The appointment is booked.")
    @mock.patch("ai_agent.services.generate_anthropic_plan")
    def test_ai_planner_can_extract_booking_fields(self, planner_mock, reply_mock):
        planner_mock.return_value = {
            "intent": "book_appointment",
            "confidence": 0.94,
            "date": date.today().isoformat(),
            "time": "11:00",
            "duration_minutes": 30,
            "customer_name": "John Miller",
            "phone": "+15550202",
            "email": None,
            "appointment_id": None,
            "service_id": None,
            "service_hint": None,
            "staff_member_id": None,
            "staff_hint": None,
            "title": None,
            "needs_human_support": False,
        }

        result = handle_inbound_text(
            self.client,
            "I need an appointment for John Miller today at eleven.",
            channel="web",
            use_ai=True,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "booked")
        self.assertEqual(result["ai_provider"], "anthropic")
        self.assertEqual(Appointment.objects.get().customer.full_name, "John Miller")
        planner_mock.assert_called_once()
        reply_mock.assert_called_once()

    def test_ai_books_first_available_employee_when_staff_is_not_requested(self):
        staff_a = StaffMember.objects.create(business_client=self.client, full_name="Ana Smith", role_title="Stylist")
        staff_b = StaffMember.objects.create(business_client=self.client, full_name="Mark Brown", role_title="Stylist")
        Appointment.objects.create(
            business_client=self.client,
            staff_member=staff_a,
            title="Busy slot",
            status=Appointment.STATUS_CONFIRMED,
            date=date.today(),
            start_time=time(10, 0),
            duration_minutes=30,
            channel="web",
        )

        result = handle_inbound_text(
            self.client,
            "Book appointment",
            channel="web",
            payload={
                "date": date.today(),
                "time": time(10, 0),
                "customer_name": "Emma Wilson",
                "phone": "+15550303",
            },
            use_ai=False,
        )

        self.assertEqual(result["tool_output"]["status"], "booked")
        self.assertEqual(result["tool_output"]["staff_member"], staff_b.full_name)
        self.assertEqual(Appointment.objects.filter(staff_member=staff_b).count(), 1)

    def test_ai_availability_counts_all_active_employees(self):
        StaffMember.objects.create(business_client=self.client, full_name="Ana Smith", role_title="Stylist")
        StaffMember.objects.create(business_client=self.client, full_name="Mark Brown", role_title="Stylist")

        result = handle_inbound_text(
            self.client,
            "Check free slots today",
            channel="web",
            payload={"date": date.today()},
            use_ai=False,
        )

        self.assertEqual(result["tool_output"]["free_count"], 28)
        self.assertEqual(len(result["tool_output"]["per_staff"]), 2)
