# Generated by Django 5.1.5 on 2025-04-11 04:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('langlocale', '0002_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='placeLoc',
            field=models.CharField(default='', max_length=30),
            preserve_default=False,
        ),
    ]
