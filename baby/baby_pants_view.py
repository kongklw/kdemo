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

peeingColorMap = {
    1: '乳白色',
    2: '粉色',
    3: '正常',
    4: '黄色',
    5: '红色',
    6: '浓茶色',
}

stoolColorMap = {
    1: '墨绿色',
    2: '绿色',
    3: '黄色',
    4: '棕色',
    5: '红色',
    6: '黑',
    7: '灰白色',
}

stoolShapeMap = {
    1: '膏状',
    2: '泡沫样',
    3: '有奶瓣',
    4: '有食物残渣',
    5: '蛋花样',
    6: '水样便',
    7: '羊屎便',
    8: '含血便',
}

statusMap = {
    "peeing": '嘘嘘',
    "stool": '便便',
    "peeing-stool": '嘘嘘+便便',
    "dry": '干爽'}


class BabyPantsView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        use_date = params.get("use_date")
        queryset = BabyDiapers.objects.filter(user=user.id, use_date__date=use_date).order_by("-use_date")
        babyPantsCount = len(queryset)

        serializer = BabyDiapersSerializer(queryset, many=True)
        result_data = serializer.data
        status_list = []

        for item in serializer.data:
            status = item.get("tabActiveName")
            item_dict = {"id": item.get("id"), "status": statusMap.get(status), "use_date": item.get("use_date")}
            if status == "peeing":
                item_dict["peeing"] = peeingColorMap.get(item.get("peeing_color"))
            elif status == "stool":
                item_dict["stool"] = stoolColorMap.get(item.get("stool_color")) + stoolShapeMap.get(
                    item.get("stool_shape"))
            elif status == "peeing-stool":
                item_dict["peeing"] = peeingColorMap.get(item.get("peeing_color"))
                item_dict["stool"] = stoolColorMap.get(item.get("stool_color")) + stoolShapeMap.get(
                    item.get("stool_shape"))
            else:
                pass

            status_list.append(item_dict)
        if len(result_data) == 0:
            return Response({"code": 200, "data": [], "msg": "fetch all success"})

        return Response({"code": 200, "data": {"status_list": status_list, "babyPantsCount": babyPantsCount},
                         "msg": "fetch all success"})

    def post(self, request, *args, **kwargs):

        try:
            """
            babyPantsForm: {
            use_date: this.moment().format('YYYY-MM-DD HH:mm:00'),
            peeing_color: 3,
            describe: '',
            stool_shape: 1,
            stool_color: 3,
            is_leaked: false,
            brand: '好奇',
            tabActiveName
                },
            """
            user = request.user
            data = request.data
            use_date = data.get("use_date")
            tabActiveName = data.get("tabActiveName")
            peeing_color = data.get("peeing_color")
            stool_color = data.get("stool_color")
            stool_shape = data.get("stool_shape")
            brand = data.get("brand")
            is_leaked = data.get("is_leaked")
            describe = data.get("describe")

            if tabActiveName == "peeing":
                t = BabyDiapers(user=user, use_date=use_date, tabActiveName=tabActiveName, brand=brand,
                                peeing_color=peeing_color, describe=describe,
                                is_leaked=is_leaked)
            elif tabActiveName == "stool":
                t = BabyDiapers(user=user, use_date=use_date, brand=brand,
                                stool_shape=stool_shape, describe=describe,
                                stool_color=stool_color, tabActiveName=tabActiveName,
                                is_leaked=is_leaked)

            elif tabActiveName == "peeing-stool":
                t = BabyDiapers(user=user, use_date=use_date, brand=brand, peeing_color=peeing_color,
                                stool_shape=stool_shape, describe=describe, tabActiveName=tabActiveName,
                                stool_color=stool_color, is_leaked=is_leaked)

            else:
                t = BabyDiapers(user=user, use_date=use_date, brand=brand, tabActiveName=tabActiveName,
                                describe=describe, is_leaked=is_leaked)

            t.save()
            return Response({'code': 200, 'msg': 'ok', 'data': None})

        except Exception as exc:

            return Response({'code': 205, 'msg': str(exc), 'data': None})

    def delete(self, request, *args, **kwargs):

        data = request.data
        id = data.get("id")
        obj = BabyDiapers.objects.get(id=id)
        obj.delete()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})
