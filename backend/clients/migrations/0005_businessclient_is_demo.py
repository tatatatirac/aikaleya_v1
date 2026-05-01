from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0004_alter_businessclient_interface_language_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessclient",
            name="is_demo",
            field=models.BooleanField(default=False),
        ),
    ]
