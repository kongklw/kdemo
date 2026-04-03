from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('baby', '0041_remove_birthdayrecord_id_card_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='albumphoto',
            name='poster',
            field=models.ImageField(blank=True, null=True, upload_to='baby_album/posters/'),
        ),
    ]

