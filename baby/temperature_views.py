import json
import logging
import base64
import os, uuid
import time
import asyncio

from dateutil.utils import today
from rest_framework.views import APIView
from rest_framework.response import Response
from custom import MyModelViewSet
from .models import BabyInfo, FeedMilk, SleepLog, BabyDiapers, BabyExpense, Temperature, TodoList
from .serializers import BabyInfoSerializer, FeedMilkSerializer, SleepLogSerializer, BabyDiapersSerializer, \
    BabyExpenseSerializer, TemperatureSerializer, TodoListSerializer
from utils import convert_seconds, convert_string_datetime, convert_string_date
from datetime import datetime, timedelta, date
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Sum
from zoneinfo import ZoneInfo
from decimal import Decimal, getcontext
from utils import alibaba_client
from utils.chatApp import obtain_app
from kdemo.settings import MEDIA_ROOT
from langchain_core.messages import HumanMessage
import concurrent.futures

logger = logging.getLogger(__name__)


def get_temperature(user_id, date, mode):
    # date = convert_string_date(date)
    if mode == 'today':
        objs = Temperature.objects.filter(user=user_id, measure_date=date)
    elif mode == 'week':
        start_date = date - timedelta(days=7)

        objs = Temperature.objects.filter(user=user_id, measure_date__gte=start_date, measure_date__lte=date).order_by(
            '-date')

    else:
        objs = Temperature.object.filter(user=user_id, measure_date=date)

    serializer = TemperatureSerializer(objs, many=True)
    data = serializer.data

    return data


class TemperatureView(APIView):
    def get(self, request, *args, **kwargs):
        # 根据查询date.获取一周的体温返回。
        user = request.user
        params = request.query_params
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        user_id = user.id
        objs = Temperature.objects.filter(user=user_id, measure_date__gte=start_date,
                                          measure_date__lte=end_date).order_by('-measure_date')
        serializer = TemperatureSerializer(objs, many=True)

        current_day = date.today()
        try:
            obj = Temperature.objects.get(user=user.id, measure_date=current_day)
            current_temperature = obj.temperature
        except:
            current_temperature = "未测"

        response = {'code': 200,
                    'data': {"temperature_list": serializer.data, "current_temperature": current_temperature},
                    'msg': 'ok'}
        print(response)

        return Response(response)

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            data = request.data
            print(data)

            measure_date = data.get("measure_date")
            temperature = data.get("temperature")

            if temperature <= 36.0:
                status = "低温"
            elif 36.0 < temperature < 37.0:
                status = "正常"
            elif temperature >= 37.0:
                status = "偏高"
            else:
                status = "异常"
            t = Temperature(user=user, measure_date=measure_date, temperature=temperature, status=status)
            t.save()
            return Response({'code': 200, 'msg': 'ok', 'data': None})

        except Exception as exc:

            return Response({'code': 205, 'msg': str(exc), 'data': None})

    def delete(self, request, *args, **kwargs):

        data = request.data
        id = data.get("id")
        obj = Temperature.objects.get(id=id)
        obj.delete()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})
