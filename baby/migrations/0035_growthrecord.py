import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baby', '0034_auto_album_video'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GrowthRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('measure_date', models.DateField()),
                ('height_cm', models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True)),
                ('weight_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('head_circumference_cm', models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='growth/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-measure_date', '-id'],
            },
        ),
    ]

