import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BabyInfo, FeedMilk, SleepLog, BabyDiapers, BabyExpense, Temperature, TodoList, UserAppOrder
from datetime import datetime, timedelta, date
from django.db.models import Sum
from .breast_feed_views import process_feed_chart


logger = logging.getLogger(__name__)


class DashBoardView(APIView):
    def post(self, request, *args, **kwargs):
        """Save the user's app order preference"""
        user = request.user
        app_order = request.data.get('app_order')
        
        if not app_order or not isinstance(app_order, list):
            return Response({'code': 400, 'msg': 'Invalid app_order format', 'data': None})
            
        try:
            user_order, created = UserAppOrder.objects.get_or_create(user=user)
            user_order.order = app_order
            user_order.save()
            return Response({'code': 200, 'msg': 'Order saved successfully', 'data': None})
        except Exception as e:
            logger.error(f"Error saving app order: {e}")
            return Response({'code': 500, 'msg': str(e), 'data': None})

    def get(self, request, *args, **kwargs):
        user = request.user
        # dashboard 展示 最近一周奶量综合，总共的消费总和。今日的尿不湿片数。今日的体温情况.
        today = date.today()

        basicInfo = {}
        
        # Get user app order
        try:
            user_order = UserAppOrder.objects.get(user=user)
            basicInfo["app_order"] = user_order.order
        except UserAppOrder.DoesNotExist:
            basicInfo["app_order"] = []  # Empty list means use default order

        total_milk_volumes = FeedMilk.objects.filter(user=user.id, feed_time__date=today).aggregate(
            total_milk_volumes=Sum('milk_volume', default=0))
        basicInfo["total_milk_volumes"] = total_milk_volumes.get("total_milk_volumes")
        total_amount = BabyExpense.objects.filter(user=user).aggregate(total_amount=Sum('amount', default=0))
        basicInfo["total_amount"] = total_amount.get("total_amount")
        
        # Fix: Handle multiple objects or no objects gracefully
        current_temp_obj = Temperature.objects.filter(user=user.id, measure_date=today).order_by('-id').first()
        if current_temp_obj:
            basicInfo["current_temperature"] = current_temp_obj.temperature
        else:
            basicInfo["current_temperature"] = "未测"
            
        babyPantsCount = BabyDiapers.objects.filter(user=user.id, use_date__date=today).count()
        basicInfo["babyPantsCount"] = babyPantsCount

        # 喂奶数据
        chartData = process_feed_chart(user.id)
        response = {'code': 200, 'data': {"basicInfo": basicInfo, "charData": chartData}, 'msg': 'ok'}
        print(response)
        return Response(response)
