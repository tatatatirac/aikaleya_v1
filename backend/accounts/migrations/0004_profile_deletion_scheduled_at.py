from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_profile_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="deletion_scheduled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
