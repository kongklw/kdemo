from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from datetime import date, timedelta
from .models import MenstrualSetting, MenstrualLog
from .serializers import MenstrualSettingSerializer, MenstrualLogSerializer

class PeriodOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        month_str = request.query_params.get('month')
        today = date.today()
        if month_str:
            try:
                year, mon = [int(x) for x in month_str.split('-')]
                first_day = date(year, mon, 1)
            except Exception:
                return Response({'code': 400, 'msg': 'month 格式错误', 'data': None})
        else:
            first_day = date(today.year, today.month, 1)
        if first_day.month == 12:
            next_month_first = date(first_day.year + 1, 1, 1)
        else:
            next_month_first = date(first_day.year, first_day.month + 1, 1)
        last_day = next_month_first - timedelta(days=1)

        setting = MenstrualSetting.objects.filter(user=request.user).first()
        if not setting:
            setting = MenstrualSetting.objects.create(user=request.user, cycle_length=28, period_length=5)

        logs = MenstrualLog.objects.filter(user=request.user, date__gte=first_day, date__lte=last_day)
        day_map = {l.date.isoformat(): l for l in logs}

        latest_period = MenstrualLog.objects.filter(user=request.user, is_period=True).order_by('-date').first()
        cycle_len = setting.cycle_length or 28
        period_len = setting.period_length or 5
        predict_ovulation = None
        predict_period_start = None
        fertile_start = None
        fertile_end = None
        if latest_period:
            predict_period_start = latest_period.date + timedelta(days=cycle_len)
            predict_ovulation = latest_period.date + timedelta(days=cycle_len - 14)
            fertile_start = predict_ovulation - timedelta(days=5)
            fertile_end = predict_ovulation + timedelta(days=1)

        days = []
        cur = first_day
        while cur <= last_day:
            key = cur.isoformat()
            status = []
            l = day_map.get(key)
            if l and l.is_period:
                status.append('period')
            if predict_period_start and predict_period_start <= cur < predict_period_start + timedelta(days=period_len):
                status.append('predicted_period')
            if fertile_start and fertile_start <= cur <= fertile_end:
                status.append('fertile')
                if predict_ovulation:
                    if cur == predict_ovulation:
                        status.append('ovulation')
                    elif predict_ovulation - timedelta(days=2) <= cur <= predict_ovulation - timedelta(days=1):
                        status.append('fertile_very_high')
                    elif predict_ovulation - timedelta(days=4) <= cur <= predict_ovulation - timedelta(days=3) or predict_ovulation + timedelta(days=1) <= cur <= predict_ovulation + timedelta(days=2):
                        status.append('fertile_high')
            days.append({
                'date': key,
                'status': status,
                'log': MenstrualLogSerializer(l).data if l else None
            })
            cur += timedelta(days=1)

        return Response({
            'code': 200,
            'msg': 'ok',
            'data': {
                'month': first_day.strftime('%Y-%m'),
                'days': days,
                'predict_next_ovulation': predict_ovulation.isoformat() if predict_ovulation else None,
                'predict_next_period_start': predict_period_start.isoformat() if predict_period_start else None,
                'cycle_length': cycle_len,
                'period_length': period_len
            }
        })


class PeriodLogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'code': 400, 'msg': 'date 必填', 'data': None})
        try:
            d = date.fromisoformat(date_str)
        except Exception:
            return Response({'code': 400, 'msg': 'date 格式错误', 'data': None})
        record = MenstrualLog.objects.filter(user=request.user, date=d).first()
        return Response({'code': 200, 'msg': 'ok', 'data': MenstrualLogSerializer(record).data if record else None})

    def post(self, request):
        date_str = request.data.get('date')
        if not date_str:
            return Response({'code': 400, 'msg': 'date 必填', 'data': None})
        try:
            d = date.fromisoformat(date_str)
        except Exception:
            return Response({'code': 400, 'msg': 'date 格式错误', 'data': None})
        record = MenstrualLog.objects.filter(user=request.user, date=d).first()
        is_period = request.data.get('is_period')
        flow_level = request.data.get('flow_level')
        pain_level = request.data.get('pain_level')
        had_sex = request.data.get('had_sex')
        symptoms = request.data.get('symptoms')
        basal_temp = request.data.get('basal_temp')
        weight_kg = request.data.get('weight_kg')
        mood = request.data.get('mood')
        habit_eat_on_time = request.data.get('habit_eat_on_time')
        habit_water8 = request.data.get('habit_water8')
        habit_fruits = request.data.get('habit_fruits')
        habit_exercise = request.data.get('habit_exercise')
        habit_poop = request.data.get('habit_poop')
        payload = {}
        def normalize_empty(v):
            return None if v == '' else v

        def parse_int(v):
            v = normalize_empty(v)
            if v is None:
                return None
            return int(v)

        def parse_decimal_str(v):
            v = normalize_empty(v)
            return v

        def parse_bool(v):
            if v is None:
                return None
            return v if isinstance(v, bool) else str(v).lower() in ['1', 'true', 'yes']

        if is_period is not None:
            payload['is_period'] = parse_bool(is_period)
        if flow_level is not None:
            parsed = parse_int(flow_level)
            if parsed is not None:
                payload['flow_level'] = parsed
        if pain_level is not None:
            parsed = parse_int(pain_level)
            if parsed is not None:
                payload['pain_level'] = parsed
        if had_sex is not None:
            payload['had_sex'] = parse_bool(had_sex)
        if symptoms is not None:
            payload['symptoms'] = symptoms
        if basal_temp is not None:
            payload['basal_temp'] = parse_decimal_str(basal_temp)
        if weight_kg is not None:
            payload['weight_kg'] = parse_decimal_str(weight_kg)
        if mood is not None:
            payload['mood'] = normalize_empty(mood)
        if habit_eat_on_time is not None:
            payload['habit_eat_on_time'] = parse_bool(habit_eat_on_time)
        if habit_water8 is not None:
            payload['habit_water8'] = parse_bool(habit_water8)
        if habit_fruits is not None:
            payload['habit_fruits'] = parse_bool(habit_fruits)
        if habit_exercise is not None:
            payload['habit_exercise'] = parse_bool(habit_exercise)
        if habit_poop is not None:
            payload['habit_poop'] = parse_bool(habit_poop)

        if record:
            for k, v in payload.items():
                setattr(record, k, v)
            record.save()
        else:
            record = MenstrualLog.objects.create(user=request.user, date=d, **payload)

        return Response({'code': 200, 'msg': 'ok', 'data': MenstrualLogSerializer(record).data})


class PeriodSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        s = MenstrualSetting.objects.filter(user=request.user).first()
        if not s:
            s = MenstrualSetting.objects.create(user=request.user, cycle_length=28, period_length=5)
        return Response({'code': 200, 'msg': 'ok', 'data': MenstrualSettingSerializer(s).data})

    def post(self, request):
        s = MenstrualSetting.objects.filter(user=request.user).first()
        if not s:
            s = MenstrualSetting.objects.create(user=request.user, cycle_length=28, period_length=5)
        cycle_length = request.data.get('cycle_length')
        period_length = request.data.get('period_length')
        if cycle_length is not None:
            try:
                s.cycle_length = int(cycle_length)
            except Exception:
                return Response({'code': 400, 'msg': 'cycle_length 格式错误', 'data': None})
        if period_length is not None:
            try:
                s.period_length = int(period_length)
            except Exception:
                return Response({'code': 400, 'msg': 'period_length 格式错误', 'data': None})
        s.save()
        return Response({'code': 200, 'msg': 'ok', 'data': MenstrualSettingSerializer(s).data})
