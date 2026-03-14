from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baby', '0036_babyvaccinerecord'),
    ]

    operations = [
        migrations.CreateModel(
            name='VaccineDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vaccine_key', models.CharField(max_length=100, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('dose_index', models.IntegerField(default=1)),
                ('dose_total', models.IntegerField(default=1)),
                ('fee_type', models.CharField(choices=[('free', 'FREE'), ('paid', 'PAID')], default='free', max_length=10)),
                ('description', models.CharField(blank=True, max_length=500, null=True)),
                ('months_offset', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('days_offset', models.IntegerField(default=0)),
                ('price_min', models.IntegerField(blank=True, null=True)),
                ('price_max', models.IntegerField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['months_offset', 'days_offset', 'id'],
            },
        ),
    ]

