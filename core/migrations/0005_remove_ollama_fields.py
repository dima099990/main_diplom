from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_add_ollama_settings'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sitesettings',
            name='bot_ollama_url',
        ),
        migrations.RemoveField(
            model_name='sitesettings',
            name='bot_ollama_model',
        ),
    ]
