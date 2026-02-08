from rest_framework import serializers
from .models import SportModels


class SportSerializer(serializers.ModelSerializer):

    class Meta:
        model = SportModels
        fields = "__all__"
        # user 字段通常在 view 中注入，不需要前端传递
        extra_kwargs = {'user': {'read_only': True}}

    # 移除自定义的 create 方法，使用 ModelSerializer 默认的 create 方法
    # 这样在 view 中调用 serializer.save(user=request.user) 时能正确处理