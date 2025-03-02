import json
import logging
import base64
import os, uuid
import time
import asyncio
from django.db import connection
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


class FeedMilkView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            params = request.query_params
            start_time = params.get("start_time")
            end_time = params.get("end_time")

            queryset = FeedMilk.objects.filter(user=user.id, feed_time__gte=start_time,
                                               feed_time__lte=end_time).order_by("feed_time")
            serializer = FeedMilkSerializer(queryset, many=True)
            result_data = serializer.data

            # today no data direct return
            if len(result_data) == 0:
                return Response({"code": 200, "data": [], "msg": "fetch all success"})

            pre_time = None
            for item in result_data:
                if pre_time is None:
                    item['time_different'] = '起点顿'
                    pre_time = convert_string_datetime(item.get("feed_time"))

                    '''计算第一个数据与第二个数据时间差'''
                else:
                    this_feed_time = convert_string_datetime(item.get("feed_time"))
                    time_different = this_feed_time - pre_time
                    item['time_different'] = convert_seconds(time_different.seconds)
                    pre_time = this_feed_time

            now_time = datetime.now()

            time_different = now_time - pre_time
            result_data.append({'feed_time': now_time.strftime('%Y-%m-%dT%H:%M:%S'), 'milk_volume': '还没吃',
                                'time_different': convert_seconds(time_different.seconds)})
            result_data.reverse()

            return Response({"code": 200, "data": result_data, "msg": "fetch all success"})

        except Exception as exc:

            logger.error(str(exc))
            return Response({"code": 205, "data": None, "msg": str(exc)})

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        ser_data = {'feed_time': data.get("feed_time"), 'milk_volume': int(data.get("milk_volume")), 'user': user.id}

        serializer = FeedMilkSerializer(data=ser_data)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response({'code': 205, 'msg': str(serializer.errors), 'data': None})
        return Response({'code': 200, 'msg': 'ok', 'data': None})

    def delete(self, request, *args, **kwargs):

        data = request.data
        id = data.get("id")
        obj = FeedMilk.objects.get(id=id)
        obj.delete()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})


def dictfetchall(cursor):
    """
    Return all rows from a cursor as a dict.
    Assume the column names are unique.
    """
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def process_feed_chart(user_id):
    chartData = {
        'current_day': {'xAxisData': [], 'lowData': [], 'highData': [], 'actualData': [], 'titleText': '今日奶量',
                        'yMin': 0},
        'latest_week': {'xAxisData': [], 'lowData': [], 'highData': [], 'actualData': [], 'titleText': '近15天',
                        'yMin': 600},
        'basic_info': {'milkVolumes': 0, 'refermilkVolumes': '800-1000'}}

    with connection.cursor() as cursor:
        cursor.execute(
            "select sum(milk_volume) as total_volume from kdemo.baby_feedmilk where user_id=%s and date(feed_time)=curdate();",
            [user_id])
        rows = dictfetchall(cursor)

        chartData['basic_info']['milkVolumes'] = rows[0]['total_volume']

    current_objs = FeedMilk.objects.raw(
        # f"SELECT id, CONCAT(HOUR(feed_time),':',LPAD(MINUTE(feed_time),2,'0')) as time, milk_volume FROM kdemo.baby_feedmilk where user_id={user_id} and date(feed_time)=date(NOW());")
        f"SELECT id, CONCAT(HOUR(feed_time),':',LPAD(MINUTE(feed_time),2,'0')) as time, milk_volume FROM kdemo.baby_feedmilk where user_id={user_id} and date(feed_time)=CURDATE() ORDER BY feed_time ASC;")

    for obj in current_objs:

        chartData['current_day']['lowData'].append(120)
        chartData['current_day']['highData'].append(210)
        chartData['current_day']['xAxisData'].append(obj.time)
        chartData['current_day']['actualData'].append(obj.milk_volume)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT sum(milk_volume) as day_volumes, date(feed_time) as date FROM kdemo.baby_feedmilk where user_id=%s and DATE_SUB(CURDATE(), INTERVAL 15 DAY) < date(feed_time) group by date(feed_time);",
            [user_id])
        rows = dictfetchall(cursor)
        for row in rows:
            chartData['latest_week']['lowData'].append(800)
            chartData['latest_week']['highData'].append(1000)
            chartData['latest_week']['xAxisData'].append(row['date'])
            chartData['latest_week']['actualData'].append(row['day_volumes'])
    return chartData


class FeedChart(APIView):
    def get(self, request, *args, **kwargs):
        '''
        feedChartData: {
            xAxisData: [1, 2, 3],
            lowData: [5, 5, 5],
            highData: [9, 9, 9],
            actualData: [3, 6, 9]
        },
        '''
        user = request.user
        params = request.query_params
        # start_date = params["start_date"]
        # end_date = params["end_date"]

        chartData = process_feed_chart(user.id)

        return Response({"code": 200, "data": chartData, "msg": "fetch all success"})
