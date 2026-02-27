from rest_framework import serializers
from datetime import date
from .models import (BabyInfo, FeedMilk, SleepLog, BabyDiapers,
                     BabyExpense, Temperature, TodoList, PantsBrandModel, GrowingBlogModel
                     )


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
        fields = ['create_time', 'text', 'done']


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
