from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0006_businessknowledgeentry"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientapisettings",
            name="master_prompt",
            field=models.TextField(blank=True),
        ),
    ]
