import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BabyInfo, FeedMilk, SleepLog, BabyDiapers, BabyExpense, Temperature, TodoList
from datetime import datetime, timedelta, date
from django.db.models import Sum
from .breast_feed_views import process_feed_chart


logger = logging.getLogger(__name__)


class DashBoardView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        # dashboard 展示 最近一周奶量综合，总共的消费总和。今日的尿不湿片数。今日的体温情况.
        today = date.today()

        basicInfo = {}

        total_milk_volumes = FeedMilk.objects.filter(user=user.id, feed_time__date=today).aggregate(
            total_milk_volumes=Sum('milk_volume', default=0))
        basicInfo["total_milk_volumes"] = total_milk_volumes.get("total_milk_volumes")
        total_amount = BabyExpense.objects.filter(user=user).aggregate(total_amount=Sum('amount', default=0))

        basicInfo["total_amount"] = total_amount.get("total_amount")
        try:
            obj = Temperature.objects.get(user=user.id, measure_date=today)
            current_temperature = obj.temperature
        except:
            current_temperature = "未测"
        basicInfo["current_temperature"] = current_temperature
        babyPantsCount = BabyDiapers.objects.filter(user=user.id, use_date__date=today).count()
        basicInfo["babyPantsCount"] = babyPantsCount

        # 喂奶数据
        chartData = process_feed_chart(user.id)
        response = {'code': 200, 'data': {"basicInfo": basicInfo, "charData": chartData}, 'msg': 'ok'}
        print(response)
        return Response(response)
