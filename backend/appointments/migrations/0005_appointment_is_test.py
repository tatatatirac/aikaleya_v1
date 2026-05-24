from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0004_appointment_hidden_in_calendar"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="is_test",
            field=models.BooleanField(default=False),
        ),
    ]
