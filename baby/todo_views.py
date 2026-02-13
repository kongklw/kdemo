import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import TodoList
from .serializers import TodoListSerializer, TodoTableSerializer
from datetime import datetime, timedelta, date
from django.db.models import Count
import pandas as pd
from itertools import groupby
import os

logger = logging.getLogger(__name__)


def init_items(user):
    item_list = ["AD", "钙", "益生菌", "大便"]
    for item in item_list:
        obj = TodoList(user=user, text=item)
        obj.save()


class TodoTableView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        objs = TodoList.objects.filter(user=user, create_time__gte=start_date, create_time__lte=end_date).values(
            "create_time", "text", "done")

        serializer = TodoTableSerializer(objs, many=True)
        data = serializer.data
        grouped = groupby(data, key=lambda x: x["create_time"])

        aim_list = []
        for key, group in grouped:
            aim_list.append({"date": key, "date_items": list(group)})

        aim_list.reverse()

        return Response({'code': 200, 'data': aim_list, 'msg': 'ok'})


class TodoListView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        today = date.today().strftime('%Y-%m-%d')

        objs = TodoList.objects.filter(user=user, create_time__gte=start_date, create_time__lte=end_date)
        if (start_date == end_date) and (start_date == today) and len(objs) == 0:
            # 都是今日而且为空，那么就初始化todo
            init_items(user)
            objs = TodoList.objects.filter(user=user, create_time__gte=start_date, create_time__lte=end_date)
            serializer = TodoListSerializer(objs, many=True)
            return Response({'code': 200, 'data': serializer.data, 'msg': 'ok'})
        else:
            serializer = TodoListSerializer(objs, many=True)

            return Response({'code': 200, 'data': serializer.data, 'msg': 'ok'})

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        text = data.get("text")
        done = data.get("done")

        objs = TodoList(user=user, text=text, done=done)
        objs.save()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})

    def put(self, request, *args, **kwargs):
        data = request.data
        task_id = data.get("id")
        # data['user']=user.id
        obj = TodoList.objects.get(id=task_id)
        serializer = TodoListSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})

    def delete(self, request, *args, **kwargs):
        data = request.data

        task_id = data.get("id")
        obj = TodoList.objects.get(id=task_id)
        obj.delete()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})
