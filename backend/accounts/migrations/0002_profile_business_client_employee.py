import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clients", "0002_businessclient_date_format"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="business_client",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="employee_profiles",
                to="clients.businessclient",
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("client", "Client"),
                    ("employee", "Employee"),
                ],
                default="client",
                max_length=20,
            ),
        ),
    ]
