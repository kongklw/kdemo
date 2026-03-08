from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('baby', '0032_todolist_icon_todolist_is_daily_dailyhabit'),
    ]

    operations = [
        migrations.CreateModel(
            name='BabytreeWeeklyInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(default='babytree', max_length=50)),
                ('stage', models.CharField(default='baby', max_length=20)),
                ('week_index', models.IntegerField(blank=True, null=True)),
                ('age_range_text', models.CharField(blank=True, max_length=100, null=True)),
                ('date_range_text', models.CharField(blank=True, max_length=100, null=True)),
                ('this_week_title', models.CharField(blank=True, max_length=200, null=True)),
                ('this_week_content', models.TextField(blank=True, null=True)),
                ('baby_change_text', models.TextField(blank=True, null=True)),
                ('baby_change_question', models.TextField(blank=True, null=True)),
                ('growth_quicklook', models.JSONField(blank=True, default=dict)),
                ('source_url', models.CharField(blank=True, max_length=500, null=True)),
                ('raw_payload', models.JSONField(blank=True, default=dict)),
                ('fetched_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'unique_together': {('source', 'stage', 'week_index', 'age_range_text')},
            },
        ),
    ]
