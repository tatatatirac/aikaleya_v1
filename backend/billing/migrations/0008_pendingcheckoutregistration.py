from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0007_add_lemonsqueezy_provider"),
    ]

    operations = [
        migrations.CreateModel(
            name="PendingCheckoutRegistration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("company", models.CharField(max_length=160)),
                ("full_name", models.CharField(max_length=160)),
                ("password_hash", models.CharField(max_length=256)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("country", models.CharField(blank=True, max_length=80)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "checkout",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pending_registration",
                        to="billing.checkoutsession",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
    ]
