from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BabyInfo
from .serializers import BabyInfoSerializer
import logging
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
logger = logging.getLogger(__name__)


class BabyInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            # params = request.query_params
            # name = params.get("name")

            queryset = BabyInfo.objects.filter(user=user).first()
            
            if not queryset:
                return Response({"code": 200, "data": None, "msg": "No baby info found"})
            serializer = BabyInfoSerializer(queryset, context={'request': request})
            response = {"code": 200, "data": serializer.data, "msg": "success"}
            return Response(response)
        except Exception as e:
            logger.error(str(e))
            return Response({"code": 500, "data": None, "msg": str(e)})

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: BabyInfoView post hit. User: {request.user}, Data: {request.data}")
        try:
            data = request.data
            user = request.user

            # Check if user already has baby info
            instance = BabyInfo.objects.filter(user=user).first()
            print('是否有instance',instance)
            if instance:
                # Update existing record
                serializer = BabyInfoSerializer(instance, data=data, partial=True, context={'request': request})
            else:
                # Create new record
                print(1111111)
                serializer = BabyInfoSerializer(data=data, context={'request': request})
                print(22222222222)

            if serializer.is_valid():
                print(3333333)
                # Save with user context
                serializer.save(user=user)
                print(44444444)
                return Response({'code': 200, 'msg': 'ok', 'data': serializer.data})
            else:
                print(555555555555)
                raise serializers.ValidationError(serializer.errors)

            logger.error(f"BabyInfo validation error: {serializer.errors}")
            return Response({'code': 400, 'msg': str(serializer.errors), 'data': None})
        except Exception as e:
            logger.exception("BabyInfo unhandled exception")
            return Response({"code": 500, "data": None, "msg": str(e)})
