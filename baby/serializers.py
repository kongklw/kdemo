from rest_framework import serializers
from datetime import date
from django.conf import settings
import boto3
from botocore.config import Config
import re
from urllib.parse import quote
from fileUpload.models import File
from .models import (BabyInfo, FeedMilk, SleepLog, BabyDiapers,
                     BabyExpense, Temperature, TodoList, PantsBrandModel, GrowingBlogModel,
                     BabyAlbum, AlbumPhoto, DailyHabit, GrowthRecord, MenstrualSetting, MenstrualLog, BirthdayRecord
                     )

def _absolute_url(request, url: str) -> str:
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if request:
        return request.build_absolute_uri(url)
    return url


def _get_s3_client():
    verify = True
    if hasattr(settings, 'MINIO_VERIFY_SSL'):
        verify = bool(settings.MINIO_VERIFY_SSL)
    return boto3.client(
        's3',
        aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
        aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
        endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
        region_name=getattr(settings, 'AWS_S3_REGION_NAME', None),
        verify=verify,
        config=Config(
            signature_version=getattr(settings, 'AWS_S3_SIGNATURE_VERSION', 's3v4'),
            s3={'addressing_style': getattr(settings, 'AWS_S3_ADDRESSING_STYLE', 'path')},
        ),
    )

_RICH_TEXT_FILE_SRC_RE = re.compile(r'(?P<base>(?:https?://[^"\'<>\s]+)?)'
                                   r'(?P<api>/prod-api)?/media/(?P<key>files/[^"\'<>\s]+)')


def _rewrite_rich_text_media(html: str) -> str:
    if not html:
        return html
    if '/file/r' in html:
        return html

    def _sub(m):
        base = m.group('base') or ''
        api = m.group('api') or ''
        key = m.group('key') or ''
        return f'{base}{api}/file/r?key={quote(key)}'

    return _RICH_TEXT_FILE_SRC_RE.sub(_sub, html)


class DailyHabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyHabit
        fields = '__all__'
        read_only_fields = ['user']

class GrowingBlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrowingBlogModel
        exclude = ['user', ]
        # fields = '__all__'

    # def create(self, validated_data):
    #     data = self.context["user"]
    #     print('hhhhhhhhhhhhhhhhhhhhhhh', type(data), data)
    #     return GrowingBlogModel.objects.create(user=self.context["user"], **validated_data)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['content'] = _rewrite_rich_text_media(rep.get('content') or '')
        return rep


class BabyInfoSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    image_full = serializers.SerializerMethodField()

    class Meta:
        model = BabyInfo
        fields = ['id', 'user', 'name', 'birthday', 'birth_weight', 'birth_height', 'gender', 'image', 'image_full', 'status', 'birth_week', 'is_sensitive', 'is_only_child']
        read_only_fields = ['user']

    def get_status(self, obj):
        if obj.birthday:
            return '育儿中' if obj.birthday <= date.today() else '待产中'
        return '备孕中'

    def get_image_full(self, obj):
        request = self.context.get('request') if isinstance(self.context, dict) else None
        if not getattr(obj, 'image', None):
            return ''
        key = getattr(obj.image, 'name', None) or ''
        if not key:
            return ''

        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if bucket:
                s3 = _get_s3_client()
                try:
                    return s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=600,
                    )
                except Exception:
                    pass

            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            if not media_url.endswith('/'):
                media_url = f'{media_url}/'
            return _absolute_url(request, f'{media_url}{key.lstrip("/")}')

        try:
            return _absolute_url(request, obj.image.url)
        except Exception:
            return ''


class MenstrualSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenstrualSetting
        fields = '__all__'
        read_only_fields = ['user']


class MenstrualLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenstrualLog
        fields = '__all__'
        read_only_fields = ['user']


class TodoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TodoList
        fields = '__all__'


class TodoTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TodoList
        fields = ['create_time', 'text', 'done', 'is_daily', 'icon']


class FeedMilkSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedMilk
        fields = '__all__'


class TemperatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Temperature
        fields = '__all__'


class SleepLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SleepLog
        fields = '__all__'


class BabyDiapersSerializer(serializers.ModelSerializer):
    class Meta:
        model = BabyDiapers
        fields = '__all__'


class PantsBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = PantsBrandModel
        fields = '__all__'


class BabyExpenseSerializer(serializers.ModelSerializer):
    image_url_full = serializers.SerializerMethodField()

    class Meta:
        model = BabyExpense
        fields = '__all__'

    def get_image_url_full(self, obj):
        raw = getattr(obj, 'image_url', None) or ''
        raw = str(raw).strip()
        if not raw:
            return ''
        if raw.startswith('data:image/'):
            return raw
        if raw.startswith('http://') or raw.startswith('https://'):
            return raw

        request = self.context.get('request') if isinstance(self.context, dict) else None

        file_obj = File.objects.filter(user_id=getattr(obj, 'user_id', None), file=raw).first()
        if file_obj and getattr(file_obj, 'file', None):
            try:
                return _absolute_url(request, file_obj.file.url)
            except Exception:
                pass

        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if bucket:
                s3 = _get_s3_client()
                try:
                    url = s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={'Bucket': bucket, 'Key': raw},
                        ExpiresIn=600,
                    )
                    return url
                except Exception:
                    pass

        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        if not media_url.endswith('/'):
            media_url = f'{media_url}/'
        return _absolute_url(request, f'{media_url}{raw.lstrip("/")}')

def _calc_age_str(birthday, target_date):
    if not birthday or not target_date:
        return ""

    if target_date < birthday:
        return "出生前"

    def _days_in_month(y, m):
        if m == 12:
            return (date(y + 1, 1, 1) - date(y, 12, 1)).days
        return (date(y, m + 1, 1) - date(y, m, 1)).days

    years = 0
    while True:
        next_year = birthday.year + years + 1
        next_day = min(birthday.day, _days_in_month(next_year, birthday.month))
        next_date = date(next_year, birthday.month, next_day)
        if next_date > target_date:
            break
        years += 1

    months = 0
    while True:
        total_months = months + 1
        target_year = birthday.year + years
        target_month = birthday.month + total_months

        target_year += (target_month - 1) // 12
        target_month = ((target_month - 1) % 12) + 1

        target_day = min(birthday.day, _days_in_month(target_year, target_month))
        next_date = date(target_year, target_month, target_day)
        if next_date > target_date:
            break
        months += 1

    anchor_year = birthday.year + years
    anchor_month = birthday.month + months
    anchor_year += (anchor_month - 1) // 12
    anchor_month = ((anchor_month - 1) % 12) + 1
    anchor_day = min(birthday.day, _days_in_month(anchor_year, anchor_month))
    anchor = date(anchor_year, anchor_month, anchor_day)

    days = (target_date - anchor).days

    parts = []
    if years > 0:
        parts.append(f"{years}岁")
    if months > 0:
        parts.append(f"{months}个月")
    if days > 0:
        parts.append(f"{days}天")
    if not parts:
        return "出生当天"
    return "".join(parts)

class GrowthRecordSerializer(serializers.ModelSerializer):
    age_description = serializers.SerializerMethodField()
    photo_full = serializers.SerializerMethodField()

    class Meta:
        model = GrowthRecord
        fields = ['id', 'user', 'measure_date', 'height_cm', 'weight_kg', 'head_circumference_cm', 'photo', 'photo_full', 'created_at', 'updated_at', 'age_description']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_age_description(self, obj):
        baby_info = BabyInfo.objects.filter(user=obj.user).first()
        if not baby_info or not baby_info.birthday:
            return ""
        return _calc_age_str(baby_info.birthday, obj.measure_date)

    def get_photo_full(self, obj):
        request = self.context.get('request') if isinstance(self.context, dict) else None
        if not getattr(obj, 'photo', None):
            return ''
        key = getattr(obj.photo, 'name', None) or ''
        if not key:
            return ''

        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if bucket:
                s3 = _get_s3_client()
                try:
                    return s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=600,
                    )
                except Exception:
                    pass

            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            if not media_url.endswith('/'):
                media_url = f'{media_url}/'
            return _absolute_url(request, f'{media_url}{key.lstrip("/")}')

        try:
            return _absolute_url(request, obj.photo.url)
        except Exception:
            return ''


class AlbumPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlbumPhoto
        fields = ['id', 'image', 'is_video', 'created_at']


class BabyAlbumSerializer(serializers.ModelSerializer):
    photos = AlbumPhotoSerializer(many=True, read_only=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    age_description = serializers.SerializerMethodField()

    class Meta:
        model = BabyAlbum
        fields = ['id', 'user', 'content', 'happened_at', 'created_at', 'visibility', 'tags', 'photos', 'age_description']
        read_only_fields = ['created_at']

    def get_age_description(self, obj):
        user = obj.user
        # Find the baby info for this user. Assume first baby for now.
        baby_info = BabyInfo.objects.filter(user=user).first()
        if not baby_info or not baby_info.birthday:
            return ""
        
        # Calculate difference between happened_at and birthday
        if not obj.happened_at:
             return ""
        
        # happened_at might be datetime or date. convert to date.
        happened_date = obj.happened_at
        if hasattr(happened_date, 'date'):
             happened_date = happened_date.date()
        
        birthday = baby_info.birthday
        if happened_date < birthday:
             return "出生前"
        
        # Calculate age
        # Simple approximation: 365 days
        delta_days = (happened_date - birthday).days
        years = delta_days // 365
        remaining_days = delta_days % 365
        months = remaining_days // 30
        days = remaining_days % 30
        
        parts = []
        if years > 0:
            parts.append(f"{years}岁")
        if months > 0:
            parts.append(f"{months}个月")
        if days > 0 and years == 0 and months == 0:
             parts.append(f"{days}天")
        elif days > 0:
             parts.append(f"{days}天")
        
        if not parts:
             return "出生当天"
        
        return "".join(parts)


class BirthdayRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirthdayRecord
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']
