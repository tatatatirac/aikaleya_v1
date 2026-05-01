from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("communications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="channel",
            field=models.CharField(
                choices=[
                    ("phone", "Telefon"),
                    ("sms", "SMS"),
                    ("whatsapp", "WhatsApp"),
                    ("viber", "Viber"),
                    ("telegram", "Telegram"),
                    ("email", "Email"),
                    ("instagram", "Instagram"),
                    ("tiktok", "TikTok"),
                    ("web", "Web"),
                ],
                max_length=30,
            ),
        ),
    ]
