import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baby', '0035_growthrecord'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BabyVaccineRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vaccine_key', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=200)),
                ('dose_index', models.IntegerField(default=1)),
                ('dose_total', models.IntegerField(default=1)),
                ('fee_type', models.CharField(choices=[('free', 'FREE'), ('paid', 'PAID')], default='free', max_length=10)),
                ('description', models.CharField(blank=True, max_length=500, null=True)),
                ('recommend_date', models.DateField()),
                ('done', models.BooleanField(default=False)),
                ('actual_date', models.DateField(blank=True, null=True)),
                ('price_min', models.IntegerField(blank=True, null=True)),
                ('price_max', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['recommend_date', 'id'],
                'unique_together': {('user', 'vaccine_key', 'recommend_date')},
            },
        ),
    ]

