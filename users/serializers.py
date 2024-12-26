from rest_framework import serializers
import re
from django_redis import get_redis_connection
from .models import User


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
