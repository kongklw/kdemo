# Generated by Django 5.1.1 on 2025-02-11 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baby', '0017_merge_20250211_1128'),
    ]

    operations = [
        migrations.RenameField(
            model_name='temperature',
            old_name='date',
            new_name='measure_date',
        ),
        migrations.AddField(
            model_name='temperature',
            name='status',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
