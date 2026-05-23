from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0003_appointment_service_appointment_staff_member_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="hidden_in_calendar",
            field=models.BooleanField(default=False),
        ),
    ]
