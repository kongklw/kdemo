import json
import logging
import base64
import os, uuid
import time
import asyncio
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


def process_chartData(data, type, need_total=False):
    total_count = 0
    xAxisData = []
    actualData = []

    if type == 'milkVolumes':

        xAxis_name = 'feed_time'
        actual_name = 'milk_volume'
        expected_count = 150
    elif type == 'temperature':

        xAxis_name = 'measure_date'
        actual_name = 'temperature'
        expected_count = '36.7'

    elif type == 'babyPants':

        xAxis_name = 'use_date'
        actual_name = 'is_leaked'
        expected_count = False
    else:

        xAxis_name = 'order_time'
        actual_name = 'amount'
        expected_count = 3000

    expectedData = [expected_count] * len(data)
    for item in data:
        xAxisData.append(item[xAxis_name])
        if need_total:
            actual = int(item[actual_name])
            total_count += actual
        else:
            actual = item[actual_name]
        actualData.append(actual)

    return {'xAxisData': xAxisData, 'expectedData': expectedData, 'actualData': actualData}, total_count


class DashBoardView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        # dashboard 展示 一天的喝奶量，总共的消费总和。今日的尿不湿片数。今日的体温情况.
        today = date.today()
        print(today)
        basicInfo = {}

        total_milk_volumes = FeedMilk.objects.filter(user=user.id, feed_time__date=today).aggregate(
            total_milk_volumes=Sum('milk_volume', default=0))
        basicInfo["total_milk_volumes"] = total_milk_volumes.get("total_milk_volumes")
        print(total_milk_volumes)
        total_amount = BabyExpense.objects.filter(user=user).aggregate(total_amount=Sum('amount', default=0))
        print('总花费', total_amount)
        basicInfo["total_amount"] = total_amount.get("total_amount")

        try:
            obj = Temperature.objects.get(user=user.id, measure_date=today)
            current_temperature = obj.temperature
        except:
            current_temperature = "未测"
        print(current_temperature)

        basicInfo["current_temperature"] = current_temperature

        babyPantsCount = BabyDiapers.objects.filter(user=user.id, use_date__date=today).count()
        print(babyPantsCount)
        basicInfo["babyPantsCount"] = babyPantsCount

        # 今日喂奶数据
        queryset = FeedMilk.objects.filter(user=user.id, feed_time__date=today).order_by("feed_time")
        serializer = FeedMilkSerializer(queryset, many=True)
        result_data = serializer.data
        milk_chart, milk_total_count = process_chartData(data=result_data, type='milkVolumes', need_total=True)
        print(milk_chart, milk_total_count)
        response = {'code': 200, 'data': {"basicInfo": basicInfo, "milk_chart": milk_chart}, 'msg': 'ok'}
        print(response)
        return Response(response)


class LineChartView(APIView):

    def process_chartData(self, data, type, need_total=False):
        total_count = 0
        xAxisData = []
        actualData = []

        if type == 'milkVolumes':

            xAxis_name = 'feed_time'
            actual_name = 'milk_volume'
            expected_count = 150
        elif type == 'temperature':

            xAxis_name = 'measure_date'
            actual_name = 'temperature'
            expected_count = '36.7'

        elif type == 'babyPants':

            xAxis_name = 'use_date'
            actual_name = 'is_leaked'
            expected_count = False
        else:

            xAxis_name = 'order_time'
            actual_name = 'amount'
            expected_count = 3000

        expectedData = [expected_count] * len(data)
        for item in data:
            xAxisData.append(item[xAxis_name])
            if need_total:
                actual = int(item[actual_name])
                total_count += actual
            else:
                actual = item[actual_name]
            actualData.append(actual)

        return {'xAxisData': xAxisData, 'expectedData': expectedData, 'actualData': actualData}, total_count

    def get(self, request, *args, **kwargs):
        user = request.user
        user_id = user.id
        params = request.query_params
        print(params)
        # date = params.get("date")
        date_time = datetime.now().strftime('%Y-%m-%d 00:00:00')
        date = datetime.now().date()

        '''
        需要完成奶量数据 两天的
        体温数据,一个月的
        尿不湿 两天的
        花费 一个月的
        '''

        '''
        奶量
        '''
        totalLineChartData = {
            'milkVolumes': {'xAxisData': [], 'expectedData': [], 'actualData': []},
            'temperature': {'xAxisData': [], 'expectedData': [], 'actualData': []},
            'babyPants': {'xAxisData': [], 'expectedData': [], 'actualData': []},
            'purchases': {'xAxisData': [], 'expectedData': [], 'actualData': []},
        }
        queryset = FeedMilk.objects.filter(user=user_id, feed_time__gte=date_time).order_by("feed_time")

        sum_milk = queryset.aggregate(Sum('milk_volume'))

        serializer = FeedMilkSerializer(queryset, many=True)
        result_data = serializer.data
        milkVolumes, milk_total_count = self.process_chartData(data=result_data, type='milkVolumes', need_total=True)
        totalLineChartData['milkVolumes'] = milkVolumes

        '''
        temperature
        '''

        try:
            t = Temperature.objects.get(user=user_id, measure_date=date)
            temperature = t.temperature
        except ObjectDoesNotExist or MultipleObjectsReturned as exc:
            logger.error(str(exc))
            temperature = '未测'

        temperature_data = get_temperature(user_id, date, 'week')
        temperature_data.reverse()
        chart_temperature, _ = self.process_chartData(data=temperature_data, type='temperature', need_total=False)
        totalLineChartData['temperature'] = chart_temperature

        '''
        babyPants
        '''

        bp_queryset = BabyDiapers.objects.filter(user=user_id, use_date__gte=date_time).order_by("use_date")
        bp_count = bp_queryset.count()
        serializer = BabyDiapersSerializer(bp_queryset, many=True)
        bp_data = serializer.data
        chart_babyPants, babyPants = self.process_chartData(data=bp_data, type='babyPants', need_total=False)
        totalLineChartData['babyPants'] = chart_babyPants

        response_data = {
            'basicInfo': {'milkVolumes': milk_total_count, 'temperature': temperature, 'babyPants': bp_count},
            'totalLineChartData': totalLineChartData}

        return Response({'code': 200, 'msg': 'ok', 'data': response_data})


class BabyExpenseViewSet(MyModelViewSet):
    serializer_class = BabyExpenseSerializer
    queryset = BabyExpense.objects.all()
