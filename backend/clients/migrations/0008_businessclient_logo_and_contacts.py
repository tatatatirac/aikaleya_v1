from django.db import migrations, models

import clients.models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0007_clientapisettings_master_prompt"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessclient",
            name="business_phone",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="businessclient",
            name="business_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="businessclient",
            name="logo_image",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=clients.models.client_logo_upload_path,
            ),
        ),
    ]
