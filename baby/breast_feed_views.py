import json
import logging
import base64
import os, uuid
import time
import asyncio
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models.functions import TruncDate
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
from kdemo.settings import MEDIA_ROOT

logger = logging.getLogger(__name__)


class FeedMilkView(APIView):
    permission_classes = [IsAuthenticated]

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

        ser_data = {
            'feed_time': data.get("feed_time"),
            'milk_volume': int(data.get("milk_volume") or 0),
            'user': user.id,
            'feed_type': data.get("feed_type", "bottle"),
            'duration_total': int(data.get("duration_total") or 0),
            'left_duration': int(data.get("left_duration") or 0),
            'right_duration': int(data.get("right_duration") or 0),
            'note': data.get("note", "")
        }

        serializer = FeedMilkSerializer(data=ser_data)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response({'code': 205, 'msg': str(serializer.errors), 'data': None})
        return Response({'code': 200, 'msg': 'ok', 'data': None})

    def put(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        feed_id = data.get("id")
        
        try:
            feed_obj = FeedMilk.objects.get(id=feed_id, user=user)
        except FeedMilk.DoesNotExist:
            return Response({'code': 404, 'msg': 'Record not found', 'data': None})

        ser_data = {
            'feed_time': data.get("feed_time"),
            'milk_volume': int(data.get("milk_volume") or 0),
            'user': user.id,
            'feed_type': data.get("feed_type", "bottle"),
            'duration_total': int(data.get("duration_total") or 0),
            'left_duration': int(data.get("left_duration") or 0),
            'right_duration': int(data.get("right_duration") or 0),
            'note': data.get("note", "")
        }

        serializer = FeedMilkSerializer(feed_obj, data=ser_data)
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

    today = date.today()

    total = FeedMilk.objects.filter(user_id=user_id, feed_time__date=today).aggregate(total=Sum('milk_volume')).get('total') or 0
    chartData['basic_info']['milkVolumes'] = int(total) if total is not None else 0

    current_qs = FeedMilk.objects.filter(user_id=user_id, feed_time__date=today).order_by('feed_time')
    for obj in current_qs:
        chartData['current_day']['lowData'].append(120)
        chartData['current_day']['highData'].append(210)
        chartData['current_day']['xAxisData'].append(obj.feed_time.strftime('%H:%M'))
        chartData['current_day']['actualData'].append(obj.milk_volume)

    start_date = today - timedelta(days=14)
    latest = (
        FeedMilk.objects.filter(user_id=user_id, feed_time__date__gte=start_date, feed_time__date__lte=today)
        .annotate(day=TruncDate('feed_time'))
        .values('day')
        .annotate(day_volumes=Sum('milk_volume'))
        .order_by('day')
    )
    for row in latest:
        d = row.get('day')
        v = row.get('day_volumes') or 0
        chartData['latest_week']['lowData'].append(800)
        chartData['latest_week']['highData'].append(1000)
        chartData['latest_week']['xAxisData'].append(d.isoformat() if d else '')
        chartData['latest_week']['actualData'].append(int(v) if v is not None else 0)
    return chartData


class FeedChart(APIView):
    permission_classes = [IsAuthenticated]

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
