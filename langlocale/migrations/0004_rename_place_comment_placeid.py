# Generated by Django 5.1.5 on 2025-04-11 04:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('langlocale', '0003_place_placeloc'),
    ]

    operations = [
        migrations.RenameField(
            model_name='comment',
            old_name='place',
            new_name='placeId',
        ),
    ]
