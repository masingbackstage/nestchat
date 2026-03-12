from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("server", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="server",
            name="avatar",
            field=models.ImageField(blank=True, null=True, upload_to="server_avatars/"),
        ),
    ]
