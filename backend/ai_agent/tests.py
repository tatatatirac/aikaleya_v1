from datetime import date, time
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from ai_agent.services import handle_inbound_text
from accounts.models import Profile
from appointments.services import aware_client_datetime
from audit_log.models import AuditLog
from appointments.models import Appointment
from billing.models import Plan
from clients.models import BusinessClient, BusinessKnowledgeEntry
from communications.models import Conversation, Message
from notifications.models import NotificationJob
from staff_services.models import BlockedTime, Service, StaffMember, WorkingHours
from support.models import SupportTicket


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

    def test_ai_asks_for_customer_before_booking(self):
        result = handle_inbound_text(
            self.client,
            "Book appointment tomorrow at 10:00",
            channel="web",
            payload={"date": date.today(), "time": time(10, 0)},
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "needs_more_details")
        self.assertIn("customer_contact", result["decision"]["missing_fields"])
        self.assertEqual(Appointment.objects.count(), 0)

    def test_ai_keeps_waiting_state_in_conversation_metadata(self):
        conversation = Conversation.objects.create(
            business_client=self.client,
            channel="web",
            language="en",
        )

        result = handle_inbound_text(
            self.client,
            "Book appointment tomorrow at 10:00",
            conversation=conversation,
            channel="web",
            payload={"date": date.today(), "time": time(10, 0)},
            use_ai=False,
        )

        conversation.refresh_from_db()
        self.assertEqual(result["conversation_state"]["status"], "waiting_for_customer")
        self.assertEqual(conversation.status, "waiting")
        self.assertEqual(conversation.metadata["ai_state"]["last_intent"], "book_appointment")

    def test_repeated_unknown_intent_escalates_to_support(self):
        conversation = Conversation.objects.create(
            business_client=self.client,
            channel="web",
            language="en",
            metadata={"ai_state": {"unknown_count": 1}},
        )

        result = handle_inbound_text(
            self.client,
            "blue square banana",
            conversation=conversation,
            channel="web",
            use_ai=False,
        )

        conversation.refresh_from_db()
        self.assertEqual(result["intent"], "support_handoff")
        self.assertEqual(conversation.status, "handoff")
        self.assertTrue(result["tool_output"]["handoff"])
        self.assertTrue(result["tool_output"]["support_ticket_id"])
        ticket = SupportTicket.objects.get(id=result["tool_output"]["support_ticket_id"])
        self.assertEqual(ticket.business_client, self.client)
        self.assertEqual(ticket.status, SupportTicket.STATUS_OPEN)
        self.assertEqual(ticket.metadata["conversation_id"], conversation.id)

    def test_ai_writes_tool_audit_log(self):
        result = handle_inbound_text(
            self.client,
            "Check free slots today",
            channel="web",
            payload={"date": date.today()},
            use_ai=False,
        )

        self.assertEqual(result["intent"], "check_availability")
        audit = AuditLog.objects.get(action="ai_agent.tool_run")
        self.assertEqual(audit.business_client, self.client)
        self.assertEqual(audit.metadata["intent"], "check_availability")

    def test_ai_requires_service_when_services_exist(self):
        Service.objects.create(
            business_client=self.client,
            name="Haircut",
            duration_minutes=30,
            price=20,
        )

        result = handle_inbound_text(
            self.client,
            "Book appointment tomorrow at 10:00",
            channel="web",
            payload={
                "date": date.today(),
                "time": time(10, 0),
                "customer_name": "Emily Carter",
                "phone": "+15550101",
            },
            use_ai=False,
        )

        self.assertEqual(result["tool_output"]["status"], "needs_more_details")
        self.assertIn("service", result["decision"]["missing_fields"])
        self.assertEqual(Appointment.objects.count(), 0)

    def test_ai_availability_respects_closed_working_day(self):
        target_date = date(2026, 5, 11)
        WorkingHours.objects.create(
            business_client=self.client,
            weekday=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(16, 0),
            is_closed=True,
        )

        result = handle_inbound_text(
            self.client,
            "Check free slots",
            channel="web",
            payload={"date": target_date},
            use_ai=False,
        )

        self.assertEqual(result["intent"], "check_availability")
        self.assertTrue(result["tool_output"]["is_closed"])
        self.assertEqual(result["tool_output"]["free_count"], 0)
        self.assertEqual(result["tool_output"]["suggested_slots"], [])

    def test_ai_booking_respects_blocked_time(self):
        target_date = date(2026, 5, 11)
        BlockedTime.objects.create(
            business_client=self.client,
            start_at=aware_client_datetime(self.client, target_date, time(10, 0)),
            end_at=aware_client_datetime(self.client, target_date, time(11, 0)),
            reason="Team break",
        )

        result = handle_inbound_text(
            self.client,
            "Book appointment",
            channel="web",
            payload={
                "date": target_date,
                "time": time(10, 0),
                "customer_name": "Emily Carter",
                "phone": "+15550101",
            },
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "time_unavailable")
        self.assertNotIn("10:00", result["tool_output"]["suggested_slots"])
        self.assertNotIn("10:30", result["tool_output"]["suggested_slots"])
        self.assertEqual(Appointment.objects.count(), 0)

    def test_ai_booking_uses_available_employee_when_another_employee_is_blocked(self):
        target_date = date(2026, 5, 11)
        blocked_staff = StaffMember.objects.create(
            business_client=self.client,
            full_name="Ana Blocked",
            role_title="Stylist",
        )
        free_staff = StaffMember.objects.create(
            business_client=self.client,
            full_name="Mark Free",
            role_title="Stylist",
        )
        BlockedTime.objects.create(
            business_client=self.client,
            staff_member=blocked_staff,
            start_at=aware_client_datetime(self.client, target_date, time(10, 0)),
            end_at=aware_client_datetime(self.client, target_date, time(11, 0)),
            reason="Private appointment",
        )

        result = handle_inbound_text(
            self.client,
            "Book appointment",
            channel="web",
            payload={
                "date": target_date,
                "time": time(10, 0),
                "customer_name": "Noah Carter",
                "phone": "+15550102",
            },
            use_ai=False,
        )

        self.assertEqual(result["tool_output"]["status"], "booked")
        self.assertEqual(result["tool_output"]["staff_member"], free_staff.full_name)
        appointment = Appointment.objects.get(customer__first_name="Noah")
        self.assertEqual(appointment.staff_member_id, free_staff.id)

    def test_ai_fallback_extracts_service_customer_phone_date_and_time_from_text(self):
        Service.objects.create(
            business_client=self.client,
            name="Haircut",
            duration_minutes=45,
            price=30,
        )

        result = handle_inbound_text(
            self.client,
            "Book Haircut for Emily Carter tomorrow at 10:00. Phone +15550177",
            channel="web",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "booked")
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.customer.full_name, "Emily Carter")
        self.assertEqual(appointment.customer.phone, "+15550177")
        self.assertEqual(appointment.service.name, "Haircut")
        self.assertEqual(appointment.duration_minutes, 45)
        self.assertEqual(appointment.start_time, time(10, 0))

    def test_ai_fallback_understands_hour_suffix_and_diacritic_service(self):
        self.client.work_end = time(18, 0)
        self.client.save(update_fields=["work_end", "updated_at"])
        Service.objects.create(
            business_client=self.client,
            name="Šišanje",
            duration_minutes=30,
            price=25,
        )

        result = handle_inbound_text(
            self.client,
            "Termin za šišanje za Marka Markovića sutra u 17h telefon +38160123456",
            channel="web",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "booked")
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.customer.full_name, "Marka Markovića")
        self.assertEqual(appointment.service.name, "Šišanje")
        self.assertEqual(appointment.start_time, time(17, 0))

    def test_ai_fallback_cancels_by_name_inside_message_and_records_reason(self):
        customer = self.client.customers.create(
            first_name="Emily",
            last_name="Carter",
            phone="+15550177",
        )
        appointment = Appointment.objects.create(
            business_client=self.client,
            customer=customer,
            title="Haircut",
            status=Appointment.STATUS_CONFIRMED,
            date=date.today(),
            start_time=time(11, 0),
            duration_minutes=30,
            channel="web",
        )

        result = handle_inbound_text(
            self.client,
            "Please cancel Emily Carter appointment",
            channel="web",
            payload={"reason": "Client requested cancellation"},
            use_ai=False,
        )

        appointment.refresh_from_db()
        self.assertEqual(result["intent"], "cancel_appointment")
        self.assertEqual(result["tool_output"]["status"], "cancelled")
        self.assertEqual(appointment.status, Appointment.STATUS_CANCELLED)
        self.assertEqual(appointment.cancelled_reason, "Client requested cancellation")

    def test_ai_asks_for_target_before_cancel_without_identity(self):
        Appointment.objects.create(
            business_client=self.client,
            title="Unknown customer booking",
            status=Appointment.STATUS_CONFIRMED,
            date=date.today(),
            start_time=time(11, 0),
            duration_minutes=30,
            channel="web",
        )

        result = handle_inbound_text(
            self.client,
            "Cancel appointment",
            channel="web",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "cancel_appointment")
        self.assertEqual(result["tool_output"]["status"], "needs_more_details")
        self.assertIn("appointment_target", result["decision"]["missing_fields"])
        self.assertEqual(Appointment.objects.filter(status=Appointment.STATUS_CANCELLED).count(), 0)

    def test_ai_asks_for_target_before_reschedule_without_identity(self):
        Appointment.objects.create(
            business_client=self.client,
            title="Unknown customer booking",
            status=Appointment.STATUS_CONFIRMED,
            date=date.today(),
            start_time=time(11, 0),
            duration_minutes=30,
            channel="web",
        )

        result = handle_inbound_text(
            self.client,
            "Move appointment to tomorrow at 10:00",
            channel="web",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "reschedule_appointment")
        self.assertEqual(result["tool_output"]["status"], "needs_more_details")
        self.assertIn("appointment_target", result["decision"]["missing_fields"])
        self.assertEqual(Appointment.objects.filter(status=Appointment.STATUS_MOVED).count(), 0)

    def test_ai_reuses_external_thread_and_records_messages(self):
        first = handle_inbound_text(
            self.client,
            "Check free slots today",
            channel="whatsapp",
            external_thread_id="wa-thread-1",
            payload={"date": date.today()},
            use_ai=False,
        )
        second = handle_inbound_text(
            self.client,
            "Book appointment tomorrow at 10:00",
            channel="whatsapp",
            external_thread_id="wa-thread-1",
            payload={"date": date.today(), "time": time(10, 0)},
            use_ai=False,
        )

        self.assertEqual(first["conversation_id"], second["conversation_id"])
        conversation = Conversation.objects.get(id=first["conversation_id"])
        self.assertEqual(conversation.external_thread_id, "wa-thread-1")
        self.assertEqual(Message.objects.filter(conversation=conversation).count(), 4)
        self.assertIn("workflow_trace", second)

    def test_ai_queues_follow_up_job_after_booking(self):
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

        self.assertEqual(result["tool_output"]["status"], "booked")
        self.assertEqual(NotificationJob.objects.count(), 1)
        job = NotificationJob.objects.get()
        self.assertEqual(job.payload["event"], "appointment_created")
        self.assertEqual(job.payload["source"], "kaleya_ai")

    def test_ai_answers_from_business_knowledge_base(self):
        BusinessKnowledgeEntry.objects.create(
            business_client=self.client,
            category=BusinessKnowledgeEntry.CATEGORY_POLICY,
            language="en",
            title="Parking",
            keywords="parking car garage",
            answer="Parking is available behind the building.",
        )

        result = handle_inbound_text(
            self.client,
            "Do you have parking?",
            channel="web",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "business_info")
        self.assertEqual(result["response_text"], "Parking is available behind the building.")
        self.assertEqual(result["tool_output"]["matched_knowledge"]["title"], "Parking")

    def test_employee_ai_booking_is_scoped_to_employee_staff_member(self):
        employee_user = User.objects.create_user(username="employee", email="employee@example.com", password="emp123")
        employee_user.profile.role = Profile.ROLE_EMPLOYEE
        employee_user.profile.business_client = self.client
        employee_user.profile.save(update_fields=["role", "business_client", "updated_at"])
        employee_staff = StaffMember.objects.create(
            business_client=self.client,
            user=employee_user,
            full_name="Employee User",
            role_title="Stylist",
        )
        other_staff = StaffMember.objects.create(business_client=self.client, full_name="Other User", role_title="Stylist")

        result = handle_inbound_text(
            self.client,
            "Book appointment today at 10:00",
            channel="web",
            payload={
                "date": date.today(),
                "time": time(10, 0),
                "customer_name": "Employee Client",
                "phone": "+15550109",
                "staff_member_id": other_staff.id,
            },
            use_ai=False,
            actor=employee_user,
        )

        self.assertEqual(result["tool_output"]["status"], "booked")
        appointment = Appointment.objects.get(customer__first_name="Employee")
        self.assertEqual(appointment.staff_member_id, employee_staff.id)

    def test_employee_ai_cannot_cancel_other_staff_appointment(self):
        employee_user = User.objects.create_user(username="employee2", email="employee2@example.com", password="emp123")
        employee_user.profile.role = Profile.ROLE_EMPLOYEE
        employee_user.profile.business_client = self.client
        employee_user.profile.save(update_fields=["role", "business_client", "updated_at"])
        StaffMember.objects.create(
            business_client=self.client,
            user=employee_user,
            full_name="Employee Two",
            role_title="Stylist",
        )
        other_staff = StaffMember.objects.create(business_client=self.client, full_name="Other Two", role_title="Stylist")
        appointment = Appointment.objects.create(
            business_client=self.client,
            staff_member=other_staff,
            title="Other staff booking",
            status=Appointment.STATUS_CONFIRMED,
            date=date.today(),
            start_time=time(11, 0),
            duration_minutes=30,
            channel="web",
        )

        result = handle_inbound_text(
            self.client,
            "Cancel appointment",
            channel="web",
            payload={"appointment_id": appointment.id},
            use_ai=False,
            actor=employee_user,
        )

        appointment.refresh_from_db()
        self.assertEqual(result["intent"], "support_handoff")
        self.assertEqual(appointment.status, Appointment.STATUS_CONFIRMED)

    def test_employee_ai_cannot_cancel_other_staff_appointment_by_customer_name(self):
        employee_user = User.objects.create_user(username="employee3", email="employee3@example.com", password="emp123")
        employee_user.profile.role = Profile.ROLE_EMPLOYEE
        employee_user.profile.business_client = self.client
        employee_user.profile.save(update_fields=["role", "business_client", "updated_at"])
        StaffMember.objects.create(
            business_client=self.client,
            user=employee_user,
            full_name="Employee Three",
            role_title="Stylist",
        )
        other_staff = StaffMember.objects.create(business_client=self.client, full_name="Other Three", role_title="Stylist")
        customer = self.client.customers.create(
            first_name="Emily",
            last_name="Carter",
            phone="+15550999",
        )
        appointment = Appointment.objects.create(
            business_client=self.client,
            customer=customer,
            staff_member=other_staff,
            title="Other staff booking",
            status=Appointment.STATUS_CONFIRMED,
            date=date.today(),
            start_time=time(11, 0),
            duration_minutes=30,
            channel="web",
        )

        result = handle_inbound_text(
            self.client,
            "Cancel Emily Carter appointment",
            channel="web",
            use_ai=False,
            actor=employee_user,
        )

        appointment.refresh_from_db()
        self.assertEqual(result["intent"], "cancel_appointment")
        self.assertEqual(result["tool_output"]["status"], "needs_target")
        self.assertEqual(appointment.status, Appointment.STATUS_CONFIRMED)


class PublicIntroSpeechApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    @mock.patch(
        "ai_agent.views.synthesize_elevenlabs_speech",
        return_value={"audio_path": "voice/tts/public/kaleya-test.mp3", "audio_url": "/media/voice/tts/public/kaleya-test.mp3", "bytes": 123, "cached": True},
    )
    def test_public_intro_tts_uses_fixed_language_text_without_login(self, synthesize_mock):
        response = self.api.get("/api/ai-agent/public-intro-tts/?lang=en")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["preset"], "intro")
        self.assertEqual(response.data["language"], "en")
        self.assertIn("Kaleya", response.data["text"])
        self.assertEqual(response.data["audio_url"], "/media/voice/tts/public/kaleya-test.mp3")
        synthesize_mock.assert_called_once()

    @mock.patch(
        "ai_agent.views.synthesize_elevenlabs_speech",
        return_value={"audio_path": "voice/tts/public/kaleya-test.mp3", "audio_url": "/media/voice/tts/public/kaleya-test.mp3", "bytes": 123, "cached": True},
    )
    def test_public_intro_tts_falls_back_to_english_for_unknown_language(self, synthesize_mock):
        response = self.api.get("/api/ai-agent/public-intro-tts/?lang=unknown")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["language"], "en")
        synthesize_mock.assert_called_once()

    @mock.patch(
        "ai_agent.views.synthesize_elevenlabs_speech",
        return_value={"audio_path": "voice/tts/public/kaleya-test.mp3", "audio_url": "/media/voice/tts/public/kaleya-test.mp3", "bytes": 123, "cached": True},
    )
    def test_public_intro_tts_supports_client_greeting_preset(self, synthesize_mock):
        response = self.api.get("/api/ai-agent/public-intro-tts/?lang=en&preset=client_greeting")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["preset"], "client_greeting")
        self.assertIn("How can I help", response.data["text"])
        synthesize_mock.assert_called_once()

    def test_public_intro_tts_rejects_unknown_preset(self):
        response = self.api.get("/api/ai-agent/public-intro-tts/?lang=en&preset=free_text")

        self.assertEqual(response.status_code, 404)
