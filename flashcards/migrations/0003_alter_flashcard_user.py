# Generated by Django 5.2 on 2025-04-08 04:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flashcards', '0002_alter_flashcard_options_flashcard_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='flashcard',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='flashcards', to=settings.AUTH_USER_MODEL),
        ),
    ]
