from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BabyInfo
from .serializers import BabyInfoSerializer
import logging

logger = logging.getLogger(__name__)

class BabyInfoView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            # Get the first BabyInfo for the user, or create one if not exists?
            # Better to return empty if not exists so frontend can prompt to create.
            # But for simplicity, let's try to get or return empty.
            obj = BabyInfo.objects.filter(user=user).first()
            if obj:
                serializer = BabyInfoSerializer(obj)
                return Response({"code": 200, "data": serializer.data, "msg": "ok"})
            else:
                # Return empty data structure or specific code
                return Response({"code": 200, "data": None, "msg": "no data"})
        except Exception as e:
            logger.error(str(e))
            return Response({"code": 500, "data": None, "msg": str(e)})

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            data = request.data.copy() # Make mutable copy
            
            # Check if exists
            obj = BabyInfo.objects.filter(user=user).first()
            
            data['user'] = user.id
            
            if obj:
                serializer = BabyInfoSerializer(obj, data=data, partial=True)
            else:
                serializer = BabyInfoSerializer(data=data)

            if serializer.is_valid():
                serializer.save(user=user)
                return Response({"code": 200, "data": serializer.data, "msg": "ok"})
            else:
                return Response({"code": 400, "data": None, "msg": str(serializer.errors)})
        except Exception as e:
            logger.error(str(e))
            return Response({"code": 500, "data": None, "msg": str(e)})
