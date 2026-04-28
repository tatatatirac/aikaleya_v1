from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessclient",
            name="date_format",
            field=models.CharField(
                choices=[("dd-mm-yyyy", "DD-MM-YYYY"), ("mm-dd-yyyy", "MM-DD-YYYY")],
                default="dd-mm-yyyy",
                max_length=20,
            ),
        ),
    ]
