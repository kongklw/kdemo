from rest_framework import serializers
from datetime import date
from .models import (BabyInfo, FeedMilk, SleepLog, BabyDiapers,
                     BabyExpense, Temperature, TodoList, PantsBrandModel, GrowingBlogModel,
                     BabyAlbum, AlbumPhoto, DailyHabit
                     )

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


class BabyInfoSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = BabyInfo
        fields = ['id', 'user', 'name', 'birthday', 'birth_weight', 'birth_height', 'gender', 'image', 'status', 'birth_week', 'is_sensitive', 'is_only_child']
        read_only_fields = ['user']

    def get_status(self, obj):
        if obj.birthday:
            return '育儿中' if obj.birthday <= date.today() else '待产中'
        return '备孕中'


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
    class Meta:
        model = BabyExpense
        fields = '__all__'


class AlbumPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlbumPhoto
        fields = ['id', 'image', 'created_at']


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
