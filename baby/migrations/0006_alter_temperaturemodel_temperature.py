# Generated by Django 5.1.1 on 2024-12-28 18:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baby', '0005_temperaturemodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='temperaturemodel',
            name='temperature',
            field=models.CharField(max_length=10),
        ),
    ]
