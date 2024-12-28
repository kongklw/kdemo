from rest_framework.views import APIView
from rest_framework.response import Response
from custom import MyModelViewSet
from .models import BabyInfo, FeedMilk, SleepLog, BabyDiapers, BabyExpense, Temperature
from .serializers import BabyInfoSerializer, FeedMilkSerializer, SleepLogSerializer, BabyDiapersSerializer, \
    BabyExpenseSerializer, TemperatureSerializer
from utils import convert_seconds, convert_string_datetime, convert_string_date
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)


class BabyInfoView(APIView):
    def get(self, request, *args, **kwargs):
        params = request.query_params
        name = params.get("name")
        queryset = BabyInfo.objects.get(name=name)
        serializer = BabyInfoSerializer(queryset)
        response = {"code": 200, "data": serializer.data, "msg": "success"}
        return Response(response)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = BabyInfoSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
        return Response({'code': 200, 'msg': 'ok', 'data': None})


class FeedMilkView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            params = request.query_params
            date = params.get("date")
            queryset = FeedMilk.objects.filter(user=user.id, feed_time__gte=date).order_by("feed_time")
            serializer = FeedMilkSerializer(queryset, many=True)
            result_data = serializer.data

            # today no data direct return
            if len(result_data) == 0:
                return Response({"code": 200, "data": [], "msg": "fetch all success"})

            pre_time = None
            for item in result_data:
                if pre_time is None:
                    item['time_different'] = '今日第一顿'
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
            print(exc)

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


def get_temperature(user_id, date, mode):
    # date = convert_string_date(date)
    if mode == 'today':
        objs = Temperature.objects.filter(user=user_id, date=date)
    elif mode == 'week':
        start_date = date - timedelta(days=7)
        objs = Temperature.objects.filter(user=user_id, date__gte=start_date, date__lte=date)
    else:
        objs = Temperature.object.filter(user=user_id, date=date)

    serializer = TemperatureSerializer(objs, many=True)
    data = serializer.data
    return data


class TemperatureView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        date = params.get("date")
        mode = params.get("mode")
        user_id = user.id
        date = convert_string_date(date)
        data = get_temperature(user_id, date, mode)
        print(data)
        return Response({'code': 200, 'data': data, 'msg': 'ok'})

    def post(self, request, *args, **kwargs):

        try:
            user = request.user
            data = request.data
            print(data)
            print(user)

            t = Temperature(user=user, date=data.get('date'), temperature=data.get('temperature'))
            t.save()
            return Response({'code': 200, 'msg': 'ok', 'data': None})

        except Exception as exc:
            print(exc)
            return Response({'code': 205, 'msg': str(exc), 'data': None})


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

            xAxis_name = 'date'
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
        serializer = FeedMilkSerializer(queryset, many=True)
        result_data = serializer.data
        milkVolumes, milk_total_count = self.process_chartData(data=result_data, type='milkVolumes', need_total=True)
        totalLineChartData['milkVolumes'] = milkVolumes

        '''
        temperature
        '''

        t = Temperature.objects.get(user=user_id, date=date)
        temperature = t.temperature

        temperature_data = get_temperature(user_id, date, 'week')
        temperature_data.reverse()
        chart_temperature, _ = self.process_chartData(data=temperature_data, type='temperature', need_total=False)
        totalLineChartData['temperature'] = chart_temperature


        response_data = {'basicInfo': {'milkVolumes': milk_total_count, 'temperature': temperature},
                         'totalLineChartData': totalLineChartData}
        print(response_data)
        return Response({'code': 200, 'msg': 'ok', 'data': response_data})


class SleepLogViewSet(MyModelViewSet):
    serializer_class = SleepLogSerializer
    queryset = SleepLog.objects.all()


class BabyDiapersViewSet(MyModelViewSet):
    serializer_class = BabyDiapersSerializer
    queryset = BabyDiapers.objects.all()


class BabyExpenseViewSet(MyModelViewSet):
    serializer_class = BabyExpenseSerializer
    queryset = BabyExpense.objects.all()
