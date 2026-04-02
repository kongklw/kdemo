import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fileUpload', '0003_file_created_at_file_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bucket', models.CharField(max_length=128)),
                ('object_key', models.CharField(max_length=1024)),
                ('original_name', models.CharField(blank=True, max_length=255, null=True)),
                ('content_type', models.CharField(blank=True, max_length=255, null=True)),
                ('size_bytes', models.BigIntegerField(blank=True, null=True)),
                ('etag', models.CharField(blank=True, max_length=255, null=True)),
                ('is_video', models.BooleanField(default=False)),
                ('purpose', models.CharField(max_length=64)),
                ('ref_type', models.CharField(blank=True, max_length=64, null=True)),
                ('ref_id', models.BigIntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('init', 'init'), ('uploaded', 'uploaded'), ('bound', 'bound'), ('deleted', 'deleted')], default='init', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
