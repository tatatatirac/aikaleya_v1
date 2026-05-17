from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_profile_deletion_scheduled_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="is_onboarded",
            field=models.BooleanField(default=False),
        ),
    ]
