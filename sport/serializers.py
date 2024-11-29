from rest_framework import serializers
from .models import SportModels


class SportSerializer(serializers.ModelSerializer):

    class Meta:
        model =SportModels
        fields = "__all__"

    def create(self, validated_data):
        sport = SportModels(
            name = validated_data['name'],
            country = validated_data['country'],
            popularity = validated_data['popularity']
        )

        sport.save()
        return sport