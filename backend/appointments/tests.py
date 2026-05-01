from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from appointments.models import Appointment, Customer
from clients.models import BusinessClient
from staff_services.models import StaffMember


class AppointmentEmployeeVisibilityTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="owner-pass",
        )
        self.owner.profile.role = "client"
        self.owner.profile.save(update_fields=["role", "updated_at"])

        self.business_client = BusinessClient.objects.create(
            owner=self.owner,
            name="Kaleya Test Salon",
            public_name="Kaleya Test Salon",
            package=BusinessClient.PACKAGE_BUSINESS_PLUS,
            work_start=time(9, 0),
            work_end=time(16, 0),
        )

        self.employee_a_user = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="emp-pass",
        )
        self.employee_a_user.profile.role = "employee"
        self.employee_a_user.profile.business_client = self.business_client
        self.employee_a_user.profile.save(update_fields=["role", "business_client", "updated_at"])

        self.employee_b_user = User.objects.create_user(
            username="marko",
            email="marko@example.com",
            password="emp-pass",
        )
        self.employee_b_user.profile.role = "employee"
        self.employee_b_user.profile.business_client = self.business_client
        self.employee_b_user.profile.save(update_fields=["role", "business_client", "updated_at"])

        self.staff_a = StaffMember.objects.create(
            business_client=self.business_client,
            user=self.employee_a_user,
            full_name="Ana Employee",
            role_title="Receptionist",
            phone="+15550177",
        )
        self.staff_b = StaffMember.objects.create(
            business_client=self.business_client,
            user=self.employee_b_user,
            full_name="Marko Employee",
            role_title="Specialist",
            phone="+15550188",
        )
        self.customer_a = Customer.objects.create(
            business_client=self.business_client,
            first_name="Emily",
            last_name="Carter",
            phone="+15551001",
        )
        self.customer_b = Customer.objects.create(
            business_client=self.business_client,
            first_name="Michael",
            last_name="Johnson",
            phone="+15551002",
        )
        self.appointment_a = Appointment.objects.create(
            business_client=self.business_client,
            customer=self.customer_a,
            staff_member=self.staff_a,
            title="Haircut",
            date=date(2026, 5, 4),
            start_time=time(10, 0),
            duration_minutes=30,
            channel="web",
        )
        self.appointment_b = Appointment.objects.create(
            business_client=self.business_client,
            customer=self.customer_b,
            staff_member=self.staff_b,
            title="Checkup",
            date=date(2026, 5, 4),
            start_time=time(11, 0),
            duration_minutes=30,
            channel="web",
        )

    def result_rows(self, response):
        payload = response.json()
        return payload["results"] if isinstance(payload, dict) and "results" in payload else payload

    def test_owner_sees_all_appointments(self):
        self.api.force_authenticate(self.owner)

        response = self.api.get("/api/appointments/appointments/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = self.result_rows(response)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["id"] for row in rows}, {self.appointment_a.id, self.appointment_b.id})

    def test_employee_sees_only_own_appointments(self):
        self.api.force_authenticate(self.employee_a_user)

        response = self.api.get("/api/appointments/appointments/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = self.result_rows(response)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], self.appointment_a.id)
        self.assertEqual(rows[0]["staff_member"], self.staff_a.id)

    def test_employee_can_create_and_cancel_own_appointments(self):
        self.api.force_authenticate(self.employee_a_user)

        create_response = self.api.post(
            "/api/appointments/appointments/",
            {
                "title": "Employee booking",
                "date": "2026-05-05",
                "start_time": "10:00:00",
                "duration_minutes": 30,
                "staff_member": self.staff_a.id,
                "channel": "web",
            },
            format="json",
        )
        cancel_response = self.api.post(
            f"/api/appointments/appointments/{self.appointment_a.id}/cancel/",
            {"reason": "Client called employee directly"},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["staff_member"], self.staff_a.id)
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.data["status"], Appointment.STATUS_CANCELLED)
        self.assertEqual(cancel_response.data["cancelled_reason"], "Client called employee directly")

    def test_employee_cannot_create_or_cancel_other_staff_appointments(self):
        self.api.force_authenticate(self.employee_a_user)

        create_response = self.api.post(
            "/api/appointments/appointments/",
            {
                "title": "Wrong employee booking",
                "date": "2026-05-05",
                "start_time": "11:00:00",
                "duration_minutes": 30,
                "staff_member": self.staff_b.id,
                "channel": "web",
            },
            format="json",
        )
        cancel_response = self.api.post(
            f"/api/appointments/appointments/{self.appointment_b.id}/cancel/",
            {"reason": "Should not be allowed"},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("staff_member", create_response.data)
        self.assertEqual(cancel_response.status_code, status.HTTP_404_NOT_FOUND)
