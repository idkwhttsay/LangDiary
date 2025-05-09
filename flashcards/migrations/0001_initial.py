# Generated by Django 5.2 on 2025-04-08 03:56

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Flashcard',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('front_text', models.TextField()),
                ('back_text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('num_revisions', models.IntegerField(default=0)),
            ],
        ),
    ]
