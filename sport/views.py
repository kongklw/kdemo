from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import SportSerializer
from .models import SportModels


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
            serializer.save()
        else:
            print(serializer.errors)


        return Response({"code": 200, "data": None, "msg": "create successful"})


class SportList(APIView):
    def get(self,request,*args,**kwargs):
        queryset = SportModels.objects.all()
        serializer = SportSerializer(queryset,many=True)
        data = serializer.data
        response = {"code":200,"data":data,"msg":"fetch all success"}
        return Response(response)