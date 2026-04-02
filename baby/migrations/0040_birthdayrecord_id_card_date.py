from django.db import migrations, models


def forwards_fill_id_card_date(apps, schema_editor):
    BirthdayRecord = apps.get_model('baby', 'BirthdayRecord')
    lunar_to_solar = None
    try:
        from baby.views import _lunar_to_solar
        lunar_to_solar = _lunar_to_solar
    except Exception:
        lunar_to_solar = None

    qs = BirthdayRecord.objects.filter(id_card_date__isnull=True)
    for r in qs.iterator():
        solar = r.solar_date
        if not solar and lunar_to_solar and r.lunar_year and r.lunar_month and r.lunar_day:
            solar = lunar_to_solar(int(r.lunar_year), int(r.lunar_month), int(r.lunar_day), bool(r.lunar_is_leap))
        if not solar:
            continue
        updates = {'id_card_date': solar}
        if not r.solar_date:
            updates['solar_date'] = solar
        BirthdayRecord.objects.filter(pk=r.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('baby', '0039_birthdayrecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='birthdayrecord',
            name='id_card_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(forwards_fill_id_card_date, migrations.RunPython.noop),
    ]
