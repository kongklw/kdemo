from rest_framework import serializers
from .models import BabyInfo, FeedMilk, SleepLog, BabyDiapers, BabyExpense, Temperature, TodoList, PantsBrandModel


class BabyInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BabyInfo
        fields = '__all__'


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
