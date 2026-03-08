from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baby', '0033_babytreeweeklyinfo'),
    ]

    operations = [
        migrations.AddField(
            model_name='albumphoto',
            name='is_video',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='albumphoto',
            name='image',
            field=models.FileField(upload_to='baby_album/'),
        ),
    ]
