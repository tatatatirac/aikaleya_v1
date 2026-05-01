import uuid

from django.db import migrations, models


def populate_public_ids(apps, schema_editor):
    checkout_session = apps.get_model("billing", "CheckoutSession")
    for session in checkout_session.objects.filter(public_id__isnull=True):
        session.public_id = uuid.uuid4()
        session.save(update_fields=["public_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0005_alter_checkoutsession_provider"),
    ]

    operations = [
        migrations.AddField(
            model_name="checkoutsession",
            name="public_id",
            field=models.UUIDField(db_index=True, editable=False, null=True),
        ),
        migrations.RunPython(populate_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="checkoutsession",
            name="public_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
