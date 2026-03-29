import json
import logging
import base64
import os, uuid
import time
import asyncio
import calendar
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from custom import MyModelViewSet
from .models import BabyInfo, FeedMilk, SleepLog, BabyDiapers, BabyExpense, Temperature, TodoList, BirthdayRecord
from .serializers import BabyInfoSerializer, FeedMilkSerializer, SleepLogSerializer, BabyDiapersSerializer, \
    BabyExpenseSerializer, TemperatureSerializer, TodoListSerializer, BirthdayRecordSerializer
from utils import convert_seconds, convert_string_datetime, convert_string_date
from datetime import datetime, timedelta, date
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Sum
from zoneinfo import ZoneInfo
from decimal import Decimal, getcontext
from kdemo.settings import MEDIA_ROOT

logger = logging.getLogger(__name__)

_LUNAR_INFO = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0,
    0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,
    0x0d520
]

_LUNAR_START = date(1900, 1, 31)


def _lunar_leap_month(y: int) -> int:
    return _LUNAR_INFO[y - 1900] & 0xF


def _lunar_leap_days(y: int) -> int:
    if _lunar_leap_month(y):
        return 30 if (_LUNAR_INFO[y - 1900] & 0x10000) else 29
    return 0


def _lunar_month_days(y: int, m: int) -> int:
    if m < 1 or m > 12:
        return 0
    return 30 if (_LUNAR_INFO[y - 1900] & (0x10000 >> m)) else 29


def _lunar_year_days(y: int) -> int:
    total = 348
    info = _LUNAR_INFO[y - 1900]
    bit = 0x8000
    while bit > 0x8:
        total += 1 if (info & bit) else 0
        bit >>= 1
    return total + _lunar_leap_days(y)


def _lunar_to_solar(y: int, m: int, d: int, is_leap: bool) -> date | None:
    if y < 1900 or y > 2100:
        return None
    if m < 1 or m > 12:
        return None
    if d < 1:
        return None

    offset = 0
    for yr in range(1900, y):
        offset += _lunar_year_days(yr)

    leap = _lunar_leap_month(y)
    for mo in range(1, m):
        offset += _lunar_month_days(y, mo)
        if leap and mo == leap:
            offset += _lunar_leap_days(y)

    if is_leap:
        if not leap or leap != m:
            is_leap = False
        else:
            offset += _lunar_month_days(y, m)

    mdays = _lunar_leap_days(y) if (is_leap and leap == m) else _lunar_month_days(y, m)
    if d > mdays:
        d = mdays

    offset += d - 1
    return _LUNAR_START + timedelta(days=offset)


def _calc_next_birthday_date(record: BirthdayRecord, today: date) -> date | None:
    if record.calendar_type == BirthdayRecord.CalendarType.SOLAR:
        if not record.solar_date:
            return None
        m = record.solar_date.month
        d = record.solar_date.day
        y = today.year
        max_day = calendar.monthrange(y, m)[1]
        d2 = min(d, max_day)
        candidate = date(y, m, d2)
        if candidate < today:
            y += 1
            max_day = calendar.monthrange(y, m)[1]
            d2 = min(d, max_day)
            candidate = date(y, m, d2)
        return candidate

    m = record.lunar_month
    d = record.lunar_day
    if not m or not d:
        return None

    y = today.year
    is_leap = bool(record.lunar_is_leap)
    candidate = _lunar_to_solar(y, int(m), int(d), is_leap)
    if candidate is None:
        return None
    if candidate < today:
        candidate = _lunar_to_solar(y + 1, int(m), int(d), is_leap)
    return candidate


def _decorate_birthday(record: BirthdayRecord) -> dict:
    data = BirthdayRecordSerializer(record).data
    today = date.today()
    next_date = _calc_next_birthday_date(record, today)
    data['next_birthday_date'] = next_date.isoformat() if next_date else None
    data['next_birthday_in_days'] = (next_date - today).days if next_date else None
    return data


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
        logger.debug("LineChart params: %s", dict(params))
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


class BirthdayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs = BirthdayRecord.objects.filter(user=request.user).order_by('-updated_at', '-id')
        items = [_decorate_birthday(x) for x in qs]
        return Response({'code': 200, 'msg': 'ok', 'data': items})

    def post(self, request, *args, **kwargs):
        payload = request.data or {}
        name = (payload.get('name') or '').strip()
        if not name:
            return Response({'code': 400, 'msg': 'name 必填', 'data': None})

        calendar_type = payload.get('calendar_type') or BirthdayRecord.CalendarType.LUNAR
        if calendar_type not in [BirthdayRecord.CalendarType.LUNAR, BirthdayRecord.CalendarType.SOLAR]:
            return Response({'code': 400, 'msg': 'calendar_type 参数错误', 'data': None})

        relation = payload.get('relation')
        data = {
            'user': request.user,
            'name': name,
            'relation': relation,
            'calendar_type': calendar_type
        }

        if calendar_type == BirthdayRecord.CalendarType.SOLAR:
            solar_date = payload.get('solar_date')
            if not solar_date:
                return Response({'code': 400, 'msg': 'solar_date 必填', 'data': None})
            try:
                data['solar_date'] = date.fromisoformat(solar_date)
            except Exception:
                return Response({'code': 400, 'msg': 'solar_date 格式错误', 'data': None})
        else:
            try:
                data['lunar_year'] = int(payload.get('lunar_year') or date.today().year)
            except Exception:
                return Response({'code': 400, 'msg': 'lunar_year 参数错误', 'data': None})
            try:
                data['lunar_month'] = int(payload.get('lunar_month'))
                data['lunar_day'] = int(payload.get('lunar_day'))
            except Exception:
                return Response({'code': 400, 'msg': 'lunar_month/lunar_day 必填', 'data': None})
            data['lunar_is_leap'] = bool(payload.get('lunar_is_leap'))

        record = BirthdayRecord.objects.create(**data)
        return Response({'code': 200, 'msg': 'ok', 'data': _decorate_birthday(record)})

    def put(self, request, *args, **kwargs):
        payload = request.data or {}
        rid = payload.get('id')
        if not rid:
            return Response({'code': 400, 'msg': 'id 必填', 'data': None})
        record = BirthdayRecord.objects.filter(user=request.user, id=rid).first()
        if not record:
            return Response({'code': 404, 'msg': '记录不存在', 'data': None})

        if 'name' in payload:
            record.name = (payload.get('name') or '').strip()
        if 'relation' in payload:
            record.relation = payload.get('relation')
        if 'calendar_type' in payload:
            ct = payload.get('calendar_type')
            if ct not in [BirthdayRecord.CalendarType.LUNAR, BirthdayRecord.CalendarType.SOLAR]:
                return Response({'code': 400, 'msg': 'calendar_type 参数错误', 'data': None})
            record.calendar_type = ct

        if record.calendar_type == BirthdayRecord.CalendarType.SOLAR:
            if 'solar_date' in payload:
                solar_date = payload.get('solar_date')
                if not solar_date:
                    record.solar_date = None
                else:
                    try:
                        record.solar_date = date.fromisoformat(solar_date)
                    except Exception:
                        return Response({'code': 400, 'msg': 'solar_date 格式错误', 'data': None})
            record.lunar_month = None
            record.lunar_day = None
            record.lunar_is_leap = False
            record.lunar_year = None
        else:
            if 'lunar_year' in payload:
                try:
                    record.lunar_year = int(payload.get('lunar_year') or date.today().year)
                except Exception:
                    return Response({'code': 400, 'msg': 'lunar_year 参数错误', 'data': None})
            if 'lunar_month' in payload:
                record.lunar_month = int(payload.get('lunar_month'))
            if 'lunar_day' in payload:
                record.lunar_day = int(payload.get('lunar_day'))
            if 'lunar_is_leap' in payload:
                record.lunar_is_leap = bool(payload.get('lunar_is_leap'))
            record.solar_date = None

        record.save()
        return Response({'code': 200, 'msg': 'ok', 'data': _decorate_birthday(record)})

    def delete(self, request, *args, **kwargs):
        payload = request.data or {}
        rid = payload.get('id')
        if not rid:
            return Response({'code': 400, 'msg': 'id 必填', 'data': None})
        record = BirthdayRecord.objects.filter(user=request.user, id=rid).first()
        if not record:
            return Response({'code': 404, 'msg': '记录不存在', 'data': None})
        record.delete()
        return Response({'code': 200, 'msg': 'ok', 'data': None})
