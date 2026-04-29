from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("staff_services", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffmember",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="staff_member_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
