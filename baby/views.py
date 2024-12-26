from rest_framework.views import APIView
from rest_framework.response import Response
from custom import MyModelViewSet
from .models import BabyInfo, FeedMilk, SleepLog, BabyDiapers, BabyExpense
from .serializers import BabyInfoSerializer, FeedMilkSerializer, SleepLogSerializer, BabyDiapersSerializer, \
    BabyExpenseSerializer
from utils import convert_seconds, convert_string_datetime
from datetime import datetime
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

            response = {"code": 200, "data": result_data, "msg": "fetch all success"}
            return Response(response)
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


class LineChartView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        # date = params.get("date")
        date = datetime.now().strftime('%Y-%m-%d 00:00:00')

        '''
        需要完成奶量数据 两天的
        体温数据,一个月的
        尿不湿 两天的
        花费 一个月的
        '''

        '''
        奶量
        '''
        lineChartData = {
            'milkVolume': {'xAxisData': [], 'expectedData': [], 'actualData': []},
            'bodyTemperature': {'xAxisData': [], 'expectedData': [], 'actualData': []},
            'babyPants': {'xAxisData': [], 'expectedData': [], 'actualData': []},
            'purchases': {'xAxisData': [], 'expectedData': [], 'actualData': []},
        }
        queryset = FeedMilk.objects.filter(user=user.id, feed_time__gte=date).order_by("feed_time")
        serializer = FeedMilkSerializer(queryset, many=True)
        result_data = serializer.data
        xAxisData = []
        expectedData = [150] * len(result_data)
        actualData = []

        milkVolumes = 0
        for item in result_data:
            xAxisData.append(item['feed_time'])
            milk_volume = int(item['milk_volume'])
            actualData.append(milk_volume)
            milkVolumes += milk_volume
        print(xAxisData, expectedData, actualData)
        lineChartData['milkVolume']['xAxisData'] = xAxisData
        lineChartData['milkVolume']['expectedData'] = expectedData
        lineChartData['milkVolume']['actualData'] = actualData

        print(lineChartData)
        response_data = {'basicInfo': {'milkVolumes': milkVolumes}, 'lineChartData': lineChartData}
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
