from django.shortcuts import render
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import SportSerializer
from .models import SportModels
from rest_framework.permissions import IsAuthenticated


# Create your views here.


class SportView(APIView):

    def get(self, request, *args, **kwargs):
        '''
        response单个sport
        '''
        return Response()

    def post(self, request, *args, **kwargs):
        data = request.data

        serializer = SportSerializer(data=data)
        if serializer.is_valid():
            # 关联当前用户
            serializer.save(user=request.user)
            return Response({"code": 200, "data": None, "msg": "create successful"})
        else:
            print(serializer.errors)
            return Response({"code": 400, "data": None, "msg": str(serializer.errors)})


class SportList(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # permission_classes=[]

        print('shifou ', request.user.is_authenticated)
        print('shifou2222  ', request.user)

        # 过滤当前用户的数据
        queryset = SportModels.objects.filter(user=request.user)
        serializer = SportSerializer(queryset, many=True)
        data = serializer.data
        response = {"code": 200, "data": data, "msg": "fetch all success"}
        return Response(response)
