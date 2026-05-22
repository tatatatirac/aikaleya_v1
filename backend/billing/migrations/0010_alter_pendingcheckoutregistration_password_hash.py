from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0009_paymentwebhookevent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pendingcheckoutregistration",
            name="password_hash",
            field=models.CharField(blank=True, max_length=256),
        ),
    ]
