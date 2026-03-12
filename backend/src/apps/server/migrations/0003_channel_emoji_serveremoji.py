from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("server", "0002_server_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="channel",
            name="channel_emoji",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.CreateModel(
            name="ServerEmoji",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("name", models.SlugField(max_length=50)),
                ("image", models.ImageField(upload_to="server_emojis/")),
                ("is_animated", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "server",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="emojis",
                        to="server.server",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="serveremoji",
            constraint=models.UniqueConstraint(
                fields=("server", "name"), name="server_emoji_unique_name_per_server"
            ),
        ),
    ]
