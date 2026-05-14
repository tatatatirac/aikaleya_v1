from datetime import date, datetime, time, timezone as dt_timezone
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from ai_agent.models import CustomerMemory
from ai_agent.prompts import build_salon_planner_prompt
from ai_agent.services import build_planner_context, handle_inbound_text
from ai_agent.tools import parse_requested_date, parse_requested_time
from accounts.models import Profile
from appointments.services import aware_client_datetime
from audit_log.models import AuditLog
from appointments.models import Appointment
from billing.models import Plan
from clients.models import BusinessClient, BusinessKnowledgeEntry
from communications.models import Conversation, Message
from notifications.models import NotificationJob
from staff_services.models import BlockedTime, Service, StaffMember, StaffService, WorkingHours
from support.models import SupportTicket


class AIAppointmentToolTests(TestCase):
    def setUp(self):
        fixed_now = datetime(2026, 5, 14, 6, 0, tzinfo=dt_timezone.utc)
        self.tools_now_patcher = mock.patch("ai_agent.tools.timezone.now", return_value=fixed_now)
        self.appointments_now_patcher = mock.patch("appointments.services.timezone.now", return_value=fixed_now)
        self.tools_now_patcher.start()
        self.appointments_now_patcher.start()
        self.addCleanup(self.tools_now_patcher.stop)
        self.addCleanup(self.appointments_now_patcher.stop)
        self.user = User.objects.create_user(username="client@example.com", email="client@example.com", password="test12345")
        self.client = BusinessClient.objects.create(
            owner=self.user,
            name="AI Test Business",
            package=Plan.CODE_PRO,
            interface_language="en",
            language="en",
            timezone="UTC",
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

    def test_ai_understands_serbian_availability_question_without_booking(self):
        Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            duration_minutes=30,
            price=25,
        )

        result = handle_inbound_text(
            self.client,
            "Da li ima slobodnih termina danas?",
            channel="telegram",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "check_availability")
        self.assertEqual(result["tool_output"]["free_count"], 14)
        self.assertEqual(result["decision"]["missing_fields"], [])
        self.assertIn("Ima 14 slobodnih termina", result["response_text"])

    def test_ai_understands_short_serbian_availability_question(self):
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["interface_language", "language", "updated_at"])

        result = handle_inbound_text(
            self.client,
            "ima li sta sutra",
            channel="telegram",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "check_availability")
        self.assertEqual(result["tool_output"]["free_count"], 14)
        self.assertIn("Ima 14 slobodnih termina", result["response_text"])

    def test_ai_understands_generic_termina_availability_question(self):
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["interface_language", "language", "updated_at"])

        result = handle_inbound_text(
            self.client,
            "ima li termina",
            channel="telegram",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "check_availability")
        self.assertEqual(result["tool_output"]["free_count"], 14)

    def test_week_range_availability_asks_for_day_instead_of_guessing_sunday(self):
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["interface_language", "language", "updated_at"])

        result = handle_inbound_text(
            self.client,
            "ima li sta sledece nedelje",
            channel="telegram",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "check_availability")
        self.assertEqual(result["tool_output"]["status"], "needs_weekday")
        self.assertIn("Koji dan", result["response_text"])

    def test_short_serbian_date_is_not_parsed_as_time(self):
        reference_date = date(2026, 5, 14)

        self.assertEqual(parse_requested_date("ima li sta 20.05.", reference_date=reference_date), date(2026, 5, 20))
        self.assertEqual(parse_requested_time("ima li sta 20.05."), "")
        self.assertEqual(parse_requested_date("ima li sta 2005", reference_date=reference_date), date(2026, 5, 20))
        self.assertEqual(parse_requested_time("ima li sta 2005"), "")
        self.assertEqual(parse_requested_time("moze u 1430"), "14:30")

    def test_salon_planner_prompt_contains_safety_rules_and_business_context(self):
        Service.objects.create(
            business_client=self.client,
            name="Šišanje",
            duration_minutes=30,
            price=25,
        )

        prompt = build_salon_planner_prompt(self.client)

        self.assertIn("digitalna sekretarica salona", prompt)
        self.assertIn("Vrati samo jedan JSON objekat", prompt)
        self.assertIn("AI Test Business", prompt)
        self.assertIn("Šišanje", prompt)
        self.assertIn("Django backend proverava kalendar", prompt)

    def test_ai_availability_keeps_response_language_across_supported_languages(self):
        cases = (
            ("en", "Are there available slots today?", "There are 14 available slots"),
            ("sr", "Da li ima slobodnih termina danas?", "Ima 14 slobodnih termina"),
            ("es", "Hay citas disponibles hoy?", "Hay 14 turnos disponibles"),
            ("pt", "Tem horários livres hoje?", "Há 14 horários disponíveis"),
            ("fr", "Y a-t-il des créneaux disponibles aujourd'hui?", "Il y a 14 créneaux disponibles"),
            ("it", "Ci sono appuntamenti disponibili oggi?", "Ci sono 14 slot disponibili"),
            ("de", "Gibt es freie Termine heute?", "Es gibt 14 freie Termine"),
            ("ru", "Есть свободные записи сегодня?", "Есть 14 свободных слотов"),
        )

        for expected_language, text, expected_response in cases:
            with self.subTest(language=expected_language):
                result = handle_inbound_text(
                    self.client,
                    text,
                    channel="telegram",
                    use_ai=False,
                )

                self.assertEqual(result["intent"], "check_availability")
                self.assertEqual(result["preprocess"]["language"], expected_language)
                self.assertEqual(result["tool_output"]["free_count"], 14)
                self.assertIn(expected_response, result["response_text"])

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

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_uses_client_timezone_for_today_booking(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 12, 22, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])

        result = handle_inbound_text(
            self.client,
            "Zakazi termin danas",
            channel="telegram",
            payload={
                "time": time(9, 0),
                "customer_name": "Bane Kostic",
                "phone": "+381601234567",
            },
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(result["tool_output"]["status"], "booked")
        self.assertEqual(appointment.date, date(2026, 5, 13))
        self.assertIn("2026-05-13", result["response_text"])

    def test_ai_booking_keeps_response_language_across_supported_languages(self):
        cases = (
            ("en", "Book appointment today", "The appointment is booked for", time(9, 0)),
            ("sr", "Zakazi termin danas", "Termin je zakazan za", time(9, 30)),
            ("es", "Reservar cita hoy", "La cita esta reservada para", time(10, 0)),
            ("pt", "Marcar consulta hoje", "O agendamento esta marcado para", time(10, 30)),
            ("fr", "Reserver rendez-vous aujourd'hui", "Le rendez-vous est reserve pour", time(11, 0)),
            ("it", "Prenota appuntamento oggi", "L'appuntamento e prenotato per", time(11, 30)),
            ("de", "Termin buchen heute", "Der Termin ist fuer", time(12, 0)),
            ("ru", "Записаться сегодня", "Запись назначена на", time(12, 30)),
        )

        for expected_language, text, expected_response, slot_time in cases:
            with self.subTest(language=expected_language):
                result = handle_inbound_text(
                    self.client,
                    text,
                    channel="telegram",
                    payload={
                        "date": date.today(),
                        "time": slot_time,
                        "customer_name": f"Client {expected_language}",
                        "phone": f"+1555099{slot_time.hour:02d}{slot_time.minute:02d}",
                    },
                    use_ai=False,
                )

                self.assertEqual(result["intent"], "book_appointment")
                self.assertEqual(result["preprocess"]["language"], expected_language)
                self.assertEqual(result["tool_output"]["status"], "booked")
                self.assertIn(expected_response, result["response_text"])

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

    def test_ai_resumes_booking_when_customer_answers_requested_service(self):
        Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            duration_minutes=30,
            price=25,
        )
        external_thread_id = "telegram:test-booking-followup"

        first = handle_inbound_text(
            self.client,
            "Zakazi termin danas",
            channel="telegram",
            payload={"customer_name": "Bane Kostic"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        second = handle_inbound_text(
            self.client,
            "sisianje",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        third = handle_inbound_text(
            self.client,
            "10:00",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        self.assertEqual(first["intent"], "book_appointment")
        self.assertIn("service", first["decision"]["missing_fields"])
        self.assertEqual(second["intent"], "book_appointment")
        self.assertEqual(second["preprocess"]["language"], "sr")
        self.assertEqual(second["tool_output"]["status"], "needs_time")
        self.assertIn("Kada vam odgovara", second["response_text"])
        self.assertEqual(third["intent"], "book_appointment")
        self.assertEqual(third["tool_output"]["status"], "booked")
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.service.name, "Sisanje")
        self.assertEqual(appointment.start_time, time(10, 0))

    def test_ai_confirms_memory_service_with_short_yes(self):
        service = Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            duration_minutes=30,
            price=25,
        )
        customer = self.client.customers.create(
            first_name="Bane",
            last_name="Kostic",
            phone="+38160123456",
            preferred_channel="telegram",
        )
        CustomerMemory.objects.create(
            business_client=self.client,
            customer=customer,
            last_service=service,
            identifiers={"telegram_user_id": "424242"},
        )
        external_thread_id = "telegram:test-memory-service-confirmation"

        first = handle_inbound_text(
            self.client,
            "mogu li da zakazem za sutra",
            channel="telegram",
            payload={"telegram_user_id": "424242"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        confirmed = handle_inbound_text(
            self.client,
            "moze",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        self.assertEqual(first["intent"], "book_appointment")
        self.assertIn("Da li zelite opet Šišanje", first["response_text"])
        self.assertEqual(confirmed["intent"], "book_appointment")
        self.assertEqual(confirmed["tool_output"]["status"], "needs_time")
        self.assertNotIn("service", confirmed["decision"]["missing_fields"])
        self.assertEqual(confirmed["conversation_state"]["pending_payload"]["service_hint"], "Sisanje")
        self.assertIn("Kada vam odgovara", confirmed["response_text"])
        self.assertNotIn("Dostupne usluge", first["response_text"])

    def test_ai_resumes_booking_with_natural_serbian_time_answers(self):
        for text_value, expected_time in (
            ("moze u pola 10", time(9, 30)),
            ("930", time(9, 30)),
            ("9 30", time(9, 30)),
            ("u 14 i 30", time(14, 30)),
            ("9", time(9, 0)),
        ):
            with self.subTest(text_value=text_value):
                Appointment.objects.all().delete()
                Conversation.objects.all().delete()
                Service.objects.all().delete()
                Service.objects.create(
                    business_client=self.client,
                    name="Sisanje",
                    duration_minutes=30,
                    price=25,
                )
                external_thread_id = f"telegram:test-time-{text_value}"

                handle_inbound_text(
                    self.client,
                    "Zakazi termin danas",
                    channel="telegram",
                    payload={"customer_name": "Bane Kostic"},
                    external_thread_id=external_thread_id,
                    use_ai=False,
                )
                handle_inbound_text(
                    self.client,
                    "sisanje",
                    channel="telegram",
                    external_thread_id=external_thread_id,
                    use_ai=False,
                )
                result = handle_inbound_text(
                    self.client,
                    text_value,
                    channel="telegram",
                    external_thread_id=external_thread_id,
                    use_ai=False,
                )

                appointment = Appointment.objects.get()
                self.assertEqual(result["tool_output"]["status"], "booked")
                self.assertEqual(appointment.start_time, expected_time)

    def test_ai_books_time_followup_after_availability_check(self):
        external_thread_id = "telegram:test-availability-followup-booking"

        handle_inbound_text(
            self.client,
            "mogu li da zakazem",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        availability = handle_inbound_text(
            self.client,
            "sutra sta ima slobodno",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        booked = handle_inbound_text(
            self.client,
            "moze li u pola12",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(availability["intent"], "check_availability")
        self.assertEqual(availability["conversation_state"]["status"], "waiting_for_customer")
        self.assertEqual(booked["intent"], "book_appointment")
        self.assertEqual(booked["tool_output"]["status"], "booked")
        self.assertEqual(appointment.start_time, time(11, 30))

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_books_day_after_tomorrow_with_compact_half_hour(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])

        booked = handle_inbound_text(
            self.client,
            "moze li prekosutra u pola1",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id="telegram:test-prekosutra-booking",
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(booked["intent"], "book_appointment")
        self.assertEqual(booked["tool_output"]["status"], "booked")
        self.assertEqual(appointment.date, date(2026, 5, 16))
        self.assertEqual(appointment.start_time, time(12, 30))

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_interprets_daytime_bare_hour_inside_working_hours(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])

        booked = handle_inbound_text(
            self.client,
            "zakazi mi prekosutra u 3",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id="telegram:test-daytime-hour",
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(booked["tool_output"]["status"], "booked")
        self.assertEqual(appointment.date, date(2026, 5, 16))
        self.assertEqual(appointment.start_time, time(15, 0))

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_books_natural_service_date_and_approx_time(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])
        service = Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            category="Osnovno",
            duration_minutes=30,
            price=25,
        )

        booked = handle_inbound_text(
            self.client,
            "treba mi sisanje sutra oko15",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id="telegram:test-natural-booking",
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(booked["intent"], "book_appointment")
        self.assertEqual(booked["tool_output"]["status"], "booked")
        self.assertEqual(appointment.service, service)
        self.assertEqual(appointment.date, date(2026, 5, 15))
        self.assertEqual(appointment.start_time, time(15, 0))

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_natural_service_date_without_time_asks_only_for_time(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])
        Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            category="Osnovno",
            duration_minutes=30,
            price=25,
        )

        result = handle_inbound_text(
            self.client,
            "treba mi sisanje sutra",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id="telegram:test-natural-booking-needs-time",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "needs_time")
        self.assertEqual(result["decision"]["missing_fields"], [])
        self.assertIn("Kada vam odgovara", result["response_text"])

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_closed_day_response_has_no_empty_suggestions_and_no_loop(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])
        Service.objects.create(
            business_client=self.client,
            name="AI zakazivanje",
            category="Osnovno",
            duration_minutes=30,
            price=59,
        )
        WorkingHours.objects.create(
            business_client=self.client,
            weekday=date(2026, 5, 16).weekday(),
            start_time=time(9, 0),
            end_time=time(16, 0),
            is_closed=True,
        )
        external_thread_id = "telegram:test-closed-day-no-loop"

        first = handle_inbound_text(
            self.client,
            "da ako moze za prekosutra u pola 3",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        second = handle_inbound_text(
            self.client,
            "zakazivanje",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        third = handle_inbound_text(
            self.client,
            "stvarno",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        self.assertIn("service", first["decision"]["missing_fields"])
        self.assertEqual(second["tool_output"]["status"], "time_unavailable")
        self.assertIn("neradan", second["response_text"])
        self.assertIn("Radno vreme", second["response_text"])
        self.assertNotIn("Predlozi su: .", second["response_text"])
        self.assertEqual(third["intent"], "unknown")
        self.assertNotEqual(third["tool_output"].get("status"), "time_unavailable")

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_availability_refinement_keeps_closed_day_context(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 10, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["timezone", "interface_language", "language", "updated_at"])
        WorkingHours.objects.create(
            business_client=self.client,
            weekday=date(2026, 5, 16).weekday(),
            start_time=time(9, 0),
            end_time=time(16, 0),
            is_closed=True,
        )
        external_thread_id = "telegram:test-closed-availability-refinement"

        first = handle_inbound_text(
            self.client,
            "imate li prekosutra slobodnih termina popodne",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        refined = handle_inbound_text(
            self.client,
            "a oko 14h",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        self.assertEqual(first["intent"], "check_availability")
        self.assertEqual(first["tool_output"]["date"], "2026-05-16")
        self.assertTrue(first["tool_output"]["is_closed"])
        self.assertEqual(first["conversation_state"]["status"], "waiting_for_customer")
        self.assertEqual(first["conversation_state"]["pending_payload"]["date"], "2026-05-16")
        self.assertIn("neradan", first["response_text"])
        self.assertEqual(refined["intent"], "check_availability")
        self.assertEqual(refined["tool_output"]["date"], "2026-05-16")
        self.assertTrue(refined["tool_output"]["is_closed"])
        self.assertIn("neradan", refined["response_text"])
        self.assertNotIn("Da, oko 14:00 ima slobodno", refined["response_text"])

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_keeps_requested_time_when_closed_day_moves_to_next_workday(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["timezone", "interface_language", "language", "updated_at"])
        Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            category="Osnovno",
            duration_minutes=30,
            price=25,
        )
        WorkingHours.objects.create(
            business_client=self.client,
            weekday=date(2026, 5, 16).weekday(),
            start_time=time(9, 0),
            end_time=time(16, 0),
            is_closed=True,
        )
        external_thread_id = "telegram:test-closed-day-keeps-time"

        closed_day = handle_inbound_text(
            self.client,
            "mose li sisanje u pola 3 prekosutra",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        booked = handle_inbound_text(
            self.client,
            "ok moze li u ponedeljak",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(closed_day["tool_output"]["status"], "time_unavailable")
        self.assertEqual(closed_day["tool_output"]["requested_time"], "14:30")
        self.assertEqual(booked["intent"], "book_appointment")
        self.assertEqual(booked["tool_output"]["status"], "booked")
        self.assertEqual(appointment.date, date(2026, 5, 18))
        self.assertEqual(appointment.start_time, time(14, 30))

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_bare_day_after_closed_day_changes_date_instead_of_time(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])
        Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            category="Osnovno",
            duration_minutes=30,
            price=25,
        )
        WorkingHours.objects.create(
            business_client=self.client,
            weekday=date(2026, 5, 16).weekday(),
            start_time=time(9, 0),
            end_time=time(16, 0),
            is_closed=True,
        )
        external_thread_id = "telegram:test-bare-day-after-closed-day"

        closed_day = handle_inbound_text(
            self.client,
            "zakazi sisanje prekosutra u pola 3",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        new_day = handle_inbound_text(
            self.client,
            "18",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        self.assertEqual(closed_day["tool_output"]["status"], "time_unavailable")
        self.assertEqual(closed_day["tool_output"]["date"], "2026-05-16")
        self.assertEqual(new_day["intent"], "book_appointment")
        self.assertEqual(new_day["tool_output"]["status"], "needs_time")
        self.assertEqual(new_day["tool_output"]["date"], "2026-05-18")
        self.assertNotEqual(new_day["tool_output"]["date"], closed_day["tool_output"]["date"])

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_availability_time_followup_outside_hours_reports_work_schedule(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["timezone", "interface_language", "language", "updated_at"])
        for weekday in range(7):
            WorkingHours.objects.create(
                business_client=self.client,
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(16, 0),
                is_closed=weekday >= 5,
            )
        external_thread_id = "telegram:test-outside-work-hours-followup"

        availability = handle_inbound_text(
            self.client,
            "treba mi neki slobodan termin u petak",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        outside_hours = handle_inbound_text(
            self.client,
            "moze li u pola 6",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        self.assertEqual(availability["intent"], "check_availability")
        self.assertEqual(availability["tool_output"]["date"], "2026-05-15")
        self.assertEqual(outside_hours["intent"], "book_appointment")
        self.assertEqual(outside_hours["tool_output"]["status"], "time_unavailable")
        self.assertTrue(outside_hours["tool_output"]["is_outside_work_hours"])
        self.assertEqual(outside_hours["tool_output"]["requested_time"], "17:30")
        self.assertIn("radno vreme", outside_hours["response_text"])
        self.assertIn("od ponedeljka do petka", outside_hours["response_text"])

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_availability_focuses_suggestions_around_requested_time(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 10, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["timezone", "interface_language", "language", "updated_at"])
        service = Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            category="Osnovno",
            duration_minutes=30,
            price=25,
        )
        external_thread_id = "telegram:test-availability-around-time"

        first = handle_inbound_text(
            self.client,
            "imate li sutra slobodnih termina oko 14h",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        refined = handle_inbound_text(
            self.client,
            "ali oko 14",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        booked = handle_inbound_text(
            self.client,
            "sisanje mi treba",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(first["intent"], "check_availability")
        self.assertEqual(first["tool_output"]["requested_time"], "14:00")
        self.assertTrue(first["tool_output"]["requested_time_available"])
        self.assertEqual(first["tool_output"]["suggested_slots"][0], "14:00")
        self.assertIn("oko 14:00", first["response_text"])
        self.assertEqual(refined["intent"], "check_availability")
        self.assertEqual(refined["decision"]["missing_fields"], [])
        self.assertIn("14:00", refined["response_text"])
        self.assertEqual(booked["intent"], "book_appointment")
        self.assertEqual(booked["tool_output"]["status"], "booked")
        self.assertEqual(appointment.service, service)
        self.assertEqual(appointment.date, date(2026, 5, 15))
        self.assertEqual(appointment.start_time, time(14, 0))

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_cancels_all_customer_appointments_from_conversation_memory(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["interface_language", "language", "updated_at"])
        customer = self.client.customers.create(first_name="Bane", last_name="Kostic", phone="+38160123456")
        first = Appointment.objects.create(
            business_client=self.client,
            customer=customer,
            title="Sisanje",
            status=Appointment.STATUS_CONFIRMED,
            date=date(2026, 5, 15),
            start_time=time(10, 0),
            duration_minutes=30,
            channel="telegram",
        )
        second = Appointment.objects.create(
            business_client=self.client,
            customer=customer,
            title="Konsultacija",
            status=Appointment.STATUS_CONFIRMED,
            date=date(2026, 5, 18),
            start_time=time(11, 0),
            duration_minutes=30,
            channel="telegram",
        )
        Conversation.objects.create(
            business_client=self.client,
            customer=customer,
            channel="telegram",
            external_thread_id="telegram:test-cancel-all",
            language="sr",
        )

        result = handle_inbound_text(
            self.client,
            "mogu li da otkazem sve termine",
            channel="telegram",
            external_thread_id="telegram:test-cancel-all",
            use_ai=False,
        )

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(result["intent"], "cancel_appointment")
        self.assertEqual(result["tool_output"]["status"], "cancelled")
        self.assertEqual(result["tool_output"]["cancelled_count"], 2)
        self.assertEqual(first.status, Appointment.STATUS_CANCELLED)
        self.assertEqual(second.status, Appointment.STATUS_CANCELLED)
        self.assertIn("Otkazala sam 2 termina", result["response_text"])

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_reschedule_day_number_overrides_previous_date(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])
        customer = self.client.customers.create(first_name="Bane", last_name="Kostic", phone="+38160123456")
        appointment = Appointment.objects.create(
            business_client=self.client,
            customer=customer,
            title="AI booking request",
            status=Appointment.STATUS_CONFIRMED,
            date=date(2026, 5, 15),
            start_time=time(12, 30),
            duration_minutes=30,
            channel="telegram",
            source="ai_agent",
        )
        conversation = Conversation.objects.create(
            business_client=self.client,
            customer=customer,
            channel="telegram",
            language="sr",
            metadata={
                "ai_state": {
                    "status": "completed",
                    "last_intent": "book_appointment",
                    "last_confidence": 0.9,
                    "last_appointment_id": appointment.id,
                    "last_appointment_date": "2026-05-15",
                    "last_appointment_time": "12:30",
                }
            },
        )

        date_change = handle_inbound_text(
            self.client,
            "16ti",
            conversation=conversation,
            channel="telegram",
            use_ai=False,
        )
        rescheduled = handle_inbound_text(
            self.client,
            "9:30",
            conversation=conversation,
            channel="telegram",
            use_ai=False,
        )

        appointment.refresh_from_db()
        self.assertEqual(date_change["intent"], "reschedule_appointment")
        self.assertEqual(date_change["tool_output"]["status"], "needs_time")
        self.assertEqual(date_change["tool_output"]["date"], "2026-05-16")
        self.assertEqual(rescheduled["tool_output"]["status"], "rescheduled")
        self.assertEqual(appointment.date, date(2026, 5, 16))
        self.assertEqual(appointment.start_time, time(9, 30))

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_reschedules_last_booked_appointment_from_date_followup(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 12, 22, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["timezone", "updated_at"])
        Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            duration_minutes=30,
            price=25,
        )
        external_thread_id = "telegram:test-reschedule-after-booking"

        handle_inbound_text(
            self.client,
            "Zakazi termin danas",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        handle_inbound_text(
            self.client,
            "Sisanje",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        booked = handle_inbound_text(
            self.client,
            "pola 11",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(booked["tool_output"]["status"], "booked")
        self.assertEqual(appointment.date, date(2026, 5, 13))
        self.assertEqual(appointment.start_time, time(10, 30))

        date_change = handle_inbound_text(
            self.client,
            "jel moze 14tog maja",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        self.assertEqual(date_change["intent"], "reschedule_appointment")
        self.assertEqual(date_change["tool_output"]["status"], "needs_time")
        self.assertEqual(date_change["tool_output"]["appointment_id"], appointment.id)
        self.assertEqual(date_change["tool_output"]["date"], "2026-05-14")
        self.assertIn("Slobodni termini", date_change["response_text"])

        rescheduled = handle_inbound_text(
            self.client,
            "pola 10",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        appointment.refresh_from_db()
        self.assertEqual(rescheduled["tool_output"]["status"], "rescheduled")
        self.assertEqual(appointment.status, Appointment.STATUS_MOVED)
        self.assertEqual(appointment.date, date(2026, 5, 14))
        self.assertEqual(appointment.start_time, time(9, 30))

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_reschedules_same_date_from_spoken_minutes_followup(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 0, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["timezone", "interface_language", "language", "updated_at"])
        customer = self.client.customers.create(first_name="Bane", last_name="Kostic", phone="+38160123456")
        appointment = Appointment.objects.create(
            business_client=self.client,
            customer=customer,
            title="Sisanje",
            status=Appointment.STATUS_CONFIRMED,
            date=date(2026, 5, 19),
            start_time=time(14, 0),
            duration_minutes=30,
            channel="telegram",
            source="ai_agent",
        )
        conversation = Conversation.objects.create(
            business_client=self.client,
            customer=customer,
            channel="telegram",
            external_thread_id="telegram:test-same-date-spoken-minutes",
            language="sr",
            metadata={
                "ai_state": {
                    "status": "completed",
                    "last_intent": "book_appointment",
                    "last_confidence": 0.9,
                    "last_appointment_id": appointment.id,
                    "last_appointment_date": "2026-05-19",
                    "last_appointment_time": "14:00",
                }
            },
        )

        result = handle_inbound_text(
            self.client,
            "u 14 i 30 mi treba",
            conversation=conversation,
            channel="telegram",
            use_ai=False,
        )

        appointment.refresh_from_db()
        self.assertEqual(result["intent"], "reschedule_appointment")
        self.assertEqual(result["tool_output"]["status"], "rescheduled")
        self.assertEqual(appointment.date, date(2026, 5, 19))
        self.assertEqual(appointment.start_time, time(14, 30))

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

    def test_greeting_does_not_escalate_to_support(self):
        for greeting in (
            "hi",
            "helo",
            "helloo",
            "hello",
            "pozdrav",
            "cao",
            "zdravo",
            "zdravo❤️",
            "bardan",
            "dobardan",
            "dobrovece",
            "dobrovece😁",
            "dobrojutro",
            "goodafternoon",
        ):
            with self.subTest(greeting=greeting):
                conversation = Conversation.objects.create(
                    business_client=self.client,
                    channel="telegram",
                    language="sr",
                    metadata={"ai_state": {"unknown_count": 1}},
                )

                result = handle_inbound_text(
                    self.client,
                    greeting,
                    conversation=conversation,
                    channel="telegram",
                    use_ai=False,
                )

                conversation.refresh_from_db()
                self.assertEqual(result["intent"], "business_info")
                self.assertEqual(result["tool_output"]["status"], "greeting")
                self.assertNotEqual(conversation.status, "handoff")
                self.assertEqual(SupportTicket.objects.count(), 0)

    def test_gratitude_closes_conversation_without_unknown_prompt(self):
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["interface_language", "language", "updated_at"])
        for message in ("hvala", "ok hvala", "fala", "fala vi", "okfala", "okhvala", "doviđenja", "vidimo se"):
            with self.subTest(message=message):
                conversation = Conversation.objects.create(
                    business_client=self.client,
                    channel="telegram",
                    language="sr",
                    metadata={"ai_state": {"unknown_count": 1}},
                )

                result = handle_inbound_text(
                    self.client,
                    message,
                    conversation=conversation,
                    channel="telegram",
                    use_ai=False,
                )

                conversation.refresh_from_db()
                self.assertEqual(result["intent"], "business_info")
                self.assertEqual(result["tool_output"]["status"], "gratitude")
                self.assertEqual(result["response_text"], "Hvala vama, doviđenja.")
                self.assertNotIn("zakazivanje", result["response_text"].lower())
                self.assertNotEqual(conversation.status, "handoff")
        self.assertEqual(SupportTicket.objects.count(), 0)

    def test_combined_closing_words_close_conversation_without_handoff(self):
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["interface_language", "language", "updated_at"])
        for message in ("dovidenja vidimo se", "dovidjenja vidimo se", "vidimo se cao", "cao vidimo se"):
            with self.subTest(message=message):
                conversation = Conversation.objects.create(
                    business_client=self.client,
                    channel="telegram",
                    language="sr",
                    metadata={"ai_state": {"unknown_count": 1}},
                )

                result = handle_inbound_text(
                    self.client,
                    message,
                    conversation=conversation,
                    channel="telegram",
                    use_ai=False,
                )

                conversation.refresh_from_db()
                self.assertEqual(result["intent"], "business_info")
                self.assertEqual(result["tool_output"]["status"], "gratitude")
                self.assertIn("Hvala vama", result["response_text"])
                self.assertNotEqual(conversation.status, "handoff")
        self.assertEqual(SupportTicket.objects.count(), 0)

    def test_completed_flow_closing_words_close_conversation(self):
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["interface_language", "language", "updated_at"])
        for message in ("dogovoreno", "u redu", "ok", "cao"):
            with self.subTest(message=message):
                conversation = Conversation.objects.create(
                    business_client=self.client,
                    channel="telegram",
                    language="sr",
                    metadata={"ai_state": {"last_tool_status": "booked", "last_intent": "book_appointment"}},
                )

                result = handle_inbound_text(
                    self.client,
                    message,
                    conversation=conversation,
                    channel="telegram",
                    use_ai=False,
                )

                self.assertEqual(result["intent"], "business_info")
                self.assertEqual(result["tool_output"]["status"], "gratitude")
                self.assertEqual(result["response_text"], "Hvala vama, doviđenja.")

    def test_unknown_serbian_response_avoids_form_like_intent_prompt(self):
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["interface_language", "language", "updated_at"])

        result = handle_inbound_text(
            self.client,
            "plava stolica banana",
            channel="telegram",
            use_ai=False,
        )

        self.assertEqual(result["intent"], "unknown")
        self.assertIn("Nisam sigurna", result["response_text"])
        self.assertNotIn("zakazivanje, otkazivanje, pomeranje", result["response_text"])

    @mock.patch("appointments.services.timezone.now")
    def test_today_availability_excludes_past_slots(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 16, 13, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["timezone", "interface_language", "language", "updated_at"])

        availability = handle_inbound_text(
            self.client,
            "ima li danas slobodnih termina?",
            channel="telegram",
            payload={"date": date(2026, 5, 14)},
            use_ai=False,
        )
        booking = handle_inbound_text(
            self.client,
            "Book appointment",
            channel="telegram",
            payload={
                "date": date(2026, 5, 14),
                "time": time(14, 0),
                "customer_name": "Bane Kostic",
                "phone": "+38160123456",
            },
            use_ai=False,
        )

        self.assertEqual(availability["intent"], "check_availability")
        self.assertEqual(availability["tool_output"]["free_count"], 0)
        self.assertEqual(booking["intent"], "book_appointment")
        self.assertEqual(booking["tool_output"]["status"], "time_unavailable")
        self.assertEqual(Appointment.objects.count(), 0)

    @mock.patch("ai_agent.services.timezone.now")
    def test_greeting_uses_business_name_and_local_day_part(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 6, 0, tzinfo=dt_timezone.utc)
        self.client.name = "Salon Black"
        self.client.public_name = "Salon Black"
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.timezone = "Europe/Belgrade"
        self.client.save(update_fields=["name", "public_name", "interface_language", "language", "timezone", "updated_at"])

        cases = (
            (datetime(2026, 5, 14, 6, 0, tzinfo=dt_timezone.utc), "Dobro jutro, Salon Black, izvolite."),
            (datetime(2026, 5, 14, 12, 0, tzinfo=dt_timezone.utc), "Dobar dan, Salon Black, izvolite."),
            (datetime(2026, 5, 14, 21, 0, tzinfo=dt_timezone.utc), "Dobro vece, Salon Black, izvolite."),
            (datetime(2026, 5, 14, 0, 0, tzinfo=dt_timezone.utc), "Dobro vece, Salon Black, izvolite."),
        )

        for now_value, expected_response in cases:
            with self.subTest(expected_response=expected_response):
                now_mock.return_value = now_value
                conversation = Conversation.objects.create(
                    business_client=self.client,
                    channel="telegram",
                    language="sr",
                    metadata={"ai_state": {"unknown_count": 1}},
                )

                result = handle_inbound_text(
                    self.client,
                    "dobar dan",
                    conversation=conversation,
                    channel="telegram",
                    use_ai=False,
                )

                self.assertEqual(result["intent"], "business_info")
                self.assertEqual(result["tool_output"]["status"], "greeting")
                self.assertEqual(result["response_text"], expected_response)

    @mock.patch("ai_agent.tools.timezone.now")
    def test_ai_uses_afternoon_context_and_new_time_overrides_previous_time(self, now_mock):
        now_mock.return_value = datetime(2026, 5, 14, 10, 30, tzinfo=dt_timezone.utc)
        self.client.timezone = "Europe/Belgrade"
        self.client.interface_language = "sr"
        self.client.language = "sr"
        self.client.save(update_fields=["timezone", "interface_language", "language", "updated_at"])
        Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            category="Osnovno",
            duration_minutes=30,
            price=25,
        )
        external_thread_id = "telegram:test-afternoon-natural-flow"

        needs_time = handle_inbound_text(
            self.client,
            "ttreba mi sisanje sreda popodne",
            channel="telegram",
            payload={"customer_name": "Bane Kostic", "phone": "+38160123456"},
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        availability = handle_inbound_text(
            self.client,
            "popodne da li ima slobodnih termina",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        refined = handle_inbound_text(
            self.client,
            "oko 3",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )
        booked = handle_inbound_text(
            self.client,
            "ok u pola 4",
            channel="telegram",
            external_thread_id=external_thread_id,
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        self.assertEqual(needs_time["intent"], "book_appointment")
        self.assertEqual(needs_time["tool_output"]["status"], "needs_time")
        self.assertEqual(needs_time["tool_output"]["suggested_slots"][0], "14:00")
        self.assertEqual(availability["intent"], "check_availability")
        self.assertEqual(availability["tool_output"]["date"], "2026-05-20")
        self.assertEqual(availability["tool_output"]["requested_time"], "14:00")
        self.assertEqual(availability["tool_output"]["suggested_slots"][0], "14:00")
        self.assertEqual(refined["tool_output"]["requested_time"], "15:00")
        self.assertEqual(refined["tool_output"]["suggested_slots"][0], "15:00")
        self.assertEqual(booked["tool_output"]["status"], "booked")
        self.assertEqual(appointment.date, date(2026, 5, 20))
        self.assertEqual(appointment.start_time, time(15, 30))

    def test_customer_profile_question_does_not_escalate_to_support(self):
        customer = self.client.customers.create(first_name="Bane", last_name="Kostic", phone="+38160123456")
        conversation = Conversation.objects.create(
            business_client=self.client,
            customer=customer,
            channel="telegram",
            language="sr",
            external_thread_id="telegram:test-customer-profile-info",
        )

        phone_result = handle_inbound_text(
            self.client,
            "imate li moj telefon",
            conversation=conversation,
            channel="telegram",
            use_ai=False,
        )
        name_result = handle_inbound_text(
            self.client,
            "ime",
            conversation=conversation,
            channel="telegram",
            use_ai=False,
        )

        self.assertEqual(phone_result["intent"], "business_info")
        self.assertEqual(phone_result["tool_output"]["status"], "customer_profile")
        self.assertIn("+38160123456", phone_result["response_text"])
        self.assertEqual(name_result["intent"], "business_info")
        self.assertEqual(name_result["tool_output"]["status"], "customer_profile")
        self.assertIn("Bane Kostic", name_result["response_text"])
        self.assertEqual(SupportTicket.objects.count(), 0)

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
        self.assertIn("Haircut", result["response_text"])
        self.assertEqual(Appointment.objects.count(), 0)

    def test_ai_lists_available_services_when_service_is_missing(self):
        Service.objects.create(
            business_client=self.client,
            name="AI zakazivanje",
            category="Osnovno",
            duration_minutes=30,
            price=59,
        )
        Service.objects.create(
            business_client=self.client,
            name="Konsultacija",
            category="Osnovno",
            duration_minutes=30,
            price=25,
        )

        result = handle_inbound_text(
            self.client,
            "Zakazi termin danas",
            channel="telegram",
            payload={"customer_name": "Bane Kostic"},
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertIn("service", result["decision"]["missing_fields"])
        self.assertIn("Dostupne usluge: AI zakazivanje, Konsultacija", result["response_text"])

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

    def test_ai_booking_rejects_occupied_exact_slot(self):
        service = Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            duration_minutes=30,
            price=25,
        )
        existing_customer = self.client.customers.create(first_name="Existing", phone="+15550101")
        target_date = date(2026, 5, 19)
        Appointment.objects.create(
            business_client=self.client,
            customer=existing_customer,
            service=service,
            title="Existing booking",
            status=Appointment.STATUS_CONFIRMED,
            date=target_date,
            start_time=time(14, 30),
            duration_minutes=30,
            channel="telegram",
            source="ai_agent",
        )

        result = handle_inbound_text(
            self.client,
            "Book appointment",
            channel="web",
            payload={
                "date": target_date,
                "time": time(14, 30),
                "service_id": service.id,
                "customer_name": "Bane Kostic",
                "phone": "+38160123456",
            },
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "time_unavailable")
        self.assertEqual(result["tool_output"]["requested_time"], "14:30")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_basic_booking_rejects_staff_slot_as_global_capacity(self):
        self.client.package = Plan.CODE_BASIC
        self.client.save(update_fields=["package", "updated_at"])
        service = Service.objects.create(
            business_client=self.client,
            name="Farbanje",
            duration_minutes=30,
            price=45,
        )
        staff_member = StaffMember.objects.create(
            business_client=self.client,
            full_name="Ana Stylist",
            role_title="Stylist",
            is_active=True,
        )
        StaffService.objects.create(staff_member=staff_member, service=service, is_active=True)
        existing_customer = self.client.customers.create(first_name="Existing", phone="+15550101")
        target_date = date(2026, 5, 18)
        Appointment.objects.create(
            business_client=self.client,
            customer=existing_customer,
            staff_member=staff_member,
            service=service,
            title="Existing booking",
            status=Appointment.STATUS_CONFIRMED,
            date=target_date,
            start_time=time(12, 0),
            duration_minutes=30,
            channel="telegram",
            source="ai_agent",
        )

        result = handle_inbound_text(
            self.client,
            "moze li farbanje u 12",
            channel="telegram",
            payload={
                "date": target_date,
                "service_id": service.id,
                "customer_name": "Bane Kostic",
                "phone": "+38160123456",
            },
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "time_unavailable")
        self.assertEqual(result["tool_output"]["requested_time"], "12:00")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_ai_offers_next_available_when_day_is_full(self):
        service = Service.objects.create(
            business_client=self.client,
            name="Sisanje",
            duration_minutes=30,
            price=25,
        )
        target_date = date(2026, 5, 18)
        BlockedTime.objects.create(
            business_client=self.client,
            start_at=aware_client_datetime(self.client, target_date, time(9, 0)),
            end_at=aware_client_datetime(self.client, target_date, time(16, 0)),
            reason="Fully booked",
        )

        result = handle_inbound_text(
            self.client,
            "Book appointment",
            channel="web",
            payload={
                "date": target_date,
                "time": time(12, 0),
                "service_id": service.id,
                "customer_name": "Bane Kostic",
                "phone": "+38160123456",
            },
            use_ai=False,
        )

        self.assertEqual(result["intent"], "book_appointment")
        self.assertEqual(result["tool_output"]["status"], "time_unavailable")
        self.assertEqual(result["tool_output"]["next_available_slot"]["date"], "2026-05-19")
        self.assertIn("first available slot", result["response_text"])

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

    def test_ai_cancel_keeps_response_language(self):
        customer = self.client.customers.create(
            first_name="Marko",
            last_name="Markovic",
            phone="+38160111111",
        )
        appointment = Appointment.objects.create(
            business_client=self.client,
            customer=customer,
            title="Test termin",
            status=Appointment.STATUS_CONFIRMED,
            date=date.today(),
            start_time=time(13, 0),
            duration_minutes=30,
            channel="telegram",
        )

        result = handle_inbound_text(
            self.client,
            "Otkazi termin za Marko Markovic",
            channel="telegram",
            payload={"appointment_id": appointment.id, "reason": "Test cancel"},
            use_ai=False,
        )

        appointment.refresh_from_db()
        self.assertEqual(result["intent"], "cancel_appointment")
        self.assertEqual(result["preprocess"]["language"], "sr")
        self.assertEqual(result["tool_output"]["status"], "cancelled")
        self.assertEqual(appointment.status, Appointment.STATUS_CANCELLED)
        self.assertIn("Termin je otkazan", result["response_text"])

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

    def test_ai_reschedule_keeps_response_language(self):
        customer = self.client.customers.create(
            first_name="Anna",
            last_name="Schmidt",
            phone="+491511111111",
        )
        appointment = Appointment.objects.create(
            business_client=self.client,
            customer=customer,
            title="Test Termin",
            status=Appointment.STATUS_CONFIRMED,
            date=date.today(),
            start_time=time(13, 30),
            duration_minutes=30,
            channel="telegram",
        )

        result = handle_inbound_text(
            self.client,
            "Termin verschieben heute",
            channel="telegram",
            payload={
                "appointment_id": appointment.id,
                "date": date.today(),
                "time": time(14, 0),
            },
            use_ai=False,
        )

        appointment.refresh_from_db()
        self.assertEqual(result["intent"], "reschedule_appointment")
        self.assertEqual(result["preprocess"]["language"], "de")
        self.assertEqual(result["tool_output"]["status"], "rescheduled")
        self.assertEqual(appointment.status, Appointment.STATUS_MOVED)
        self.assertEqual(appointment.start_time, time(14, 0))
        self.assertIn("Der Termin wurde auf", result["response_text"])

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

    def test_ai_updates_customer_memory_after_booking(self):
        service = Service.objects.create(
            business_client=self.client,
            name="Haircut",
            duration_minutes=30,
            price=30,
        )
        result = handle_inbound_text(
            self.client,
            "Book Haircut today at 10:00 for Emily Carter phone +15550177",
            channel="telegram",
            payload={
                "date": date.today(),
                "time": time(10, 0),
                "service_id": service.id,
                "customer_name": "Emily Carter",
                "phone": "+15550177",
            },
            external_thread_id="telegram:emily-memory",
            use_ai=False,
        )

        appointment = Appointment.objects.get()
        memory = CustomerMemory.objects.get(customer=appointment.customer)
        conversation = Conversation.objects.get(id=result["conversation_id"])
        planner_context = build_planner_context(
            self.client,
            conversation=conversation,
            conversation_state=result["conversation_state"],
            customer=appointment.customer,
        )

        self.assertEqual(result["tool_output"]["status"], "booked")
        self.assertEqual(conversation.customer, appointment.customer)
        self.assertEqual(memory.business_client, self.client)
        self.assertEqual(memory.last_service, service)
        self.assertEqual(memory.appointment_count, 1)
        self.assertEqual(memory.preferences["services"]["Haircut"], 1)
        self.assertEqual(memory.preferences["channels"]["telegram"], 1)
        self.assertIn("Haircut", memory.summary)
        self.assertEqual(result["customer_memory"]["last_service"], "Haircut")
        self.assertEqual(planner_context["customer_memory"]["customer_name"], "Emily Carter")

    def test_ai_identifies_returning_telegram_customer_and_suggests_memory(self):
        service = Service.objects.create(
            business_client=self.client,
            name="Haircut",
            duration_minutes=30,
            price=30,
        )
        first = handle_inbound_text(
            self.client,
            "Book Haircut today at 10:00",
            channel="telegram",
            payload={
                "date": date.today(),
                "time": time(10, 0),
                "service_id": service.id,
                "customer_name": "Emily Carter",
                "phone": "+15550177",
                "telegram_username": "emily_c",
                "telegram_user_id": "424242",
                "telegram_chat_id": "9001",
            },
            external_thread_id="telegram:first-memory-thread",
            use_ai=False,
        )
        appointment = Appointment.objects.get()
        memory = CustomerMemory.objects.get(customer=appointment.customer)

        second = handle_inbound_text(
            self.client,
            "Zakazi termin sutra",
            channel="telegram",
            payload={
                "customer_name": "Telegram User",
                "telegram_username": "emily_c",
                "telegram_user_id": "424242",
                "telegram_chat_id": "new-chat",
            },
            external_thread_id="telegram:new-memory-thread",
            use_ai=False,
        )

        second_conversation = Conversation.objects.get(id=second["conversation_id"])
        self.assertEqual(first["tool_output"]["status"], "booked")
        self.assertEqual(memory.identifiers["telegram_user_id"], "424242")
        self.assertEqual(second_conversation.customer, appointment.customer)
        self.assertEqual(second["intent"], "book_appointment")
        self.assertIn("service", second["decision"]["missing_fields"])
        self.assertNotIn("customer_contact", second["decision"]["missing_fields"])
        self.assertIn("Da li zelite opet Haircut", second["response_text"])

    def test_ai_prioritizes_favorite_time_for_returning_customer(self):
        service = Service.objects.create(
            business_client=self.client,
            name="Haircut",
            duration_minutes=30,
            price=30,
        )
        handle_inbound_text(
            self.client,
            "Book Haircut today at 10:00",
            channel="telegram",
            payload={
                "date": date.today(),
                "time": time(10, 0),
                "service_id": service.id,
                "customer_name": "Emily Carter",
                "telegram_user_id": "525252",
            },
            external_thread_id="telegram:first-time-memory-thread",
            use_ai=False,
        )

        result = handle_inbound_text(
            self.client,
            "Zakazi Haircut sutra",
            channel="telegram",
            payload={
                "telegram_user_id": "525252",
                "customer_name": "Emily Carter",
            },
            external_thread_id="telegram:second-time-memory-thread",
            use_ai=False,
        )

        self.assertEqual(result["tool_output"]["status"], "needs_time")
        self.assertEqual(result["customer_memory"]["favorite_time"], "10:00")
        self.assertIn("Mogu da ponudim ove slobodne termine: 10:00", result["response_text"])

    def test_owner_can_view_and_update_customer_memory(self):
        customer = self.client.customers.create(
            first_name="Emily",
            last_name="Carter",
            phone="+15550177",
            email="emily@example.com",
        )
        memory = CustomerMemory.objects.create(
            business_client=self.client,
            customer=customer,
            summary="Regular haircut customer.",
            routine_notes="Likes morning slots.",
            appointment_count=4,
            cancellation_count=1,
            preferences={"services": {"Haircut": 4}, "times": {"10:00": 3}},
        )
        api = APIClient()
        api.force_authenticate(self.user)

        list_response = api.get("/api/ai-agent/customer-memories/")
        update_response = api.patch(
            f"/api/ai-agent/customer-memories/{memory.id}/",
            {"routine_notes": "Prefers quiet morning appointments.", "no_show_risk": CustomerMemory.RISK_MEDIUM},
            format="json",
        )

        memory.refresh_from_db()
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["results"][0]["customer_name"], "Emily Carter")
        self.assertEqual(list_response.data["results"][0]["favorite_service"], "Haircut")
        self.assertEqual(list_response.data["results"][0]["favorite_time"], "10:00")
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(memory.routine_notes, "Prefers quiet morning appointments.")
        self.assertEqual(memory.no_show_risk, CustomerMemory.RISK_MEDIUM)

    def test_employee_cannot_view_customer_memory_list(self):
        employee_user = User.objects.create_user(username="employee", email="employee@example.com", password="emp123")
        employee_user.profile.role = Profile.ROLE_EMPLOYEE
        employee_user.profile.business_client = self.client
        employee_user.profile.save(update_fields=["role", "business_client", "updated_at"])
        customer = self.client.customers.create(first_name="Emily", last_name="Carter", phone="+15550177")
        CustomerMemory.objects.create(
            business_client=self.client,
            customer=customer,
            summary="Private owner memory.",
        )
        api = APIClient()
        api.force_authenticate(employee_user)

        response = api.get("/api/ai-agent/customer-memories/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

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


class AIAppointmentApiTests(TestCase):
    def setUp(self):
        fixed_now = datetime(2026, 5, 14, 6, 0, tzinfo=dt_timezone.utc)
        self.tools_now_patcher = mock.patch("ai_agent.tools.timezone.now", return_value=fixed_now)
        self.appointments_now_patcher = mock.patch("appointments.services.timezone.now", return_value=fixed_now)
        self.tools_now_patcher.start()
        self.appointments_now_patcher.start()
        self.addCleanup(self.tools_now_patcher.stop)
        self.addCleanup(self.appointments_now_patcher.stop)
        self.api = APIClient()
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="test12345",
        )
        self.owner.profile.role = Profile.ROLE_CLIENT
        self.owner.profile.save(update_fields=["role", "updated_at"])
        self.client = BusinessClient.objects.create(
            owner=self.owner,
            name="AI API Salon",
            package=Plan.CODE_BUSINESS_PLUS,
            interface_language="en",
            language="en",
            timezone="UTC",
            work_start=time(9, 0),
            work_end=time(16, 0),
            slot_interval_minutes=30,
        )

    def test_owner_can_book_appointment_through_inbound_text_api(self):
        self.api.force_authenticate(self.owner)

        response = self.api.post(
            "/api/ai-agent/inbound-text/",
            {
                "text": "Book appointment",
                "date": date.today().isoformat(),
                "time": "10:00",
                "customer_name": "Sofia Adams",
                "phone": "+15550123",
                "channel": "web",
                "use_ai": False,
                "include_voice": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["intent"], "book_appointment")
        self.assertEqual(response.data["tool_output"]["status"], "booked")
        self.assertTrue(response.data["conversation_id"])
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.customer.full_name, "Sofia Adams")
        self.assertEqual(appointment.start_time, time(10, 0))
        self.assertEqual(appointment.source, "ai_agent")

    def test_employee_booking_api_is_scoped_to_own_staff_profile(self):
        employee_user = User.objects.create_user(
            username="employee-api",
            email="employee-api@example.com",
            password="emp123",
        )
        employee_user.profile.role = Profile.ROLE_EMPLOYEE
        employee_user.profile.business_client = self.client
        employee_user.profile.save(update_fields=["role", "business_client", "updated_at"])
        employee_staff = StaffMember.objects.create(
            business_client=self.client,
            user=employee_user,
            full_name="Employee API",
            role_title="Stylist",
        )
        other_staff = StaffMember.objects.create(
            business_client=self.client,
            full_name="Other API",
            role_title="Stylist",
        )
        self.api.force_authenticate(employee_user)

        response = self.api.post(
            "/api/ai-agent/inbound-text/",
            {
                "text": "Book appointment",
                "date": date.today().isoformat(),
                "time": "11:00",
                "customer_name": "Employee Customer",
                "phone": "+15550124",
                "staff_member_id": other_staff.id,
                "channel": "web",
                "use_ai": False,
                "include_voice": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tool_output"]["status"], "booked")
        appointment = Appointment.objects.get(customer__first_name="Employee")
        self.assertEqual(appointment.staff_member_id, employee_staff.id)

    def test_demo_client_inbound_text_api_never_uses_paid_ai_or_voice(self):
        self.client.is_demo = True
        self.client.save(update_fields=["is_demo", "updated_at"])
        self.api.force_authenticate(self.owner)

        response = self.api.post(
            "/api/ai-agent/inbound-text/",
            {
                "text": "Check free slots today",
                "date": date.today().isoformat(),
                "channel": "web",
                "use_ai": True,
                "include_voice": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["demo_mode"])
        self.assertEqual(response.data["ai_provider"], "demo-fallback")
        self.assertIsNone(response.data["voice"])
        self.assertEqual(response.data["tool_output"]["free_count"], 14)


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
