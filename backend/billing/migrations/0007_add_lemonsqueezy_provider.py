from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0006_checkoutsession_public_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="checkoutsession",
            name="provider",
            field=models.CharField(
                choices=[
                    ("manual", "Manual"),
                    ("lemonsqueezy", "Lemon Squeezy"),
                    ("paypal", "PayPal"),
                    ("stripe", "Stripe"),
                ],
                default="manual",
                max_length=40,
            ),
        ),
    ]
