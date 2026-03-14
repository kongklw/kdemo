import calendar
from datetime import date, timedelta

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BabyInfo, BabyVaccineRecord, VaccineDefinition


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    max_day = calendar.monthrange(y, m)[1]
    if d.day <= max_day:
        return date(y, m, d.day)
    overflow_days = d.day - max_day
    return date(y, m, max_day) + timedelta(days=overflow_days)


def _add_age_offset(birthday: date, months_offset: float = 0.0, days_offset: int = 0) -> date:
    whole = int(months_offset)
    frac = months_offset - whole
    d = _add_months(birthday, whole)
    if abs(frac - 0.5) < 1e-6:
        d = d + timedelta(days=15)
    if days_offset:
        d = d + timedelta(days=days_offset)
    return d


def _age_label(months_offset: float, days_offset: int) -> str:
    if months_offset == 0.0 and days_offset == 0:
        return '出生当天'
    val = months_offset
    if abs(val - int(val)) < 1e-6:
        return f'{int(val)}月龄'
    return f'{val:g}月龄'


def _get_definitions():
    return VaccineDefinition.objects.filter(is_active=True).order_by('months_offset', 'days_offset', 'id')


def _get_latest_record(user, vaccine_key: str):
    qs = BabyVaccineRecord.objects.filter(user=user, vaccine_key=vaccine_key).order_by('-updated_at', '-id')
    record = qs.first()
    if record:
        qs.exclude(id=record.id).delete()
    return record


class VaccineScheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        baby = BabyInfo.objects.filter(user=request.user).first()
        if not baby or not baby.birthday:
            return Response({'code': 400, 'msg': '请先完善宝宝信息', 'data': None})

        birthday = baby.birthday
        defs = list(_get_definitions())
        if not defs:
            return Response({
                'code': 200,
                'msg': 'ok',
                'data': {
                    'baby': {
                        'name': baby.name,
                        'birthday': baby.birthday.isoformat(),
                        'image': baby.image.url if baby.image else ''
                    },
                    'groups': [],
                    'paid_candidates': []
                }
            })

        vaccine_keys = [d.vaccine_key for d in defs]
        existing = BabyVaccineRecord.objects.filter(user=request.user, vaccine_key__in=vaccine_keys).order_by('-updated_at', '-id')
        record_map = {}
        keep_ids = set()
        for r in existing:
            if r.vaccine_key not in record_map:
                record_map[r.vaccine_key] = r
                keep_ids.add(r.id)
        if keep_ids:
            BabyVaccineRecord.objects.filter(user=request.user, vaccine_key__in=vaccine_keys).exclude(id__in=keep_ids).delete()

        groups = {}
        for d in defs:
            months_offset = float(d.months_offset)
            label = _age_label(months_offset, d.days_offset)
            r = record_map.get(d.vaccine_key)
            is_paid = d.fee_type == VaccineDefinition.FeeType.PAID
            status = 'pending'
            if not r and not is_paid:
                init_recommend_date = _add_age_offset(birthday, months_offset, d.days_offset)
                r = BabyVaccineRecord.objects.create(
                    user=request.user,
                    vaccine_key=d.vaccine_key,
                    name=d.name,
                    dose_index=d.dose_index,
                    dose_total=d.dose_total,
                    fee_type=d.fee_type,
                    description=d.description,
                    recommend_date=init_recommend_date,
                    done=False,
                    actual_date=None,
                    price_min=d.price_min,
                    price_max=d.price_max
                )
                record_map[d.vaccine_key] = r
            if is_paid and not r:
                status = 'not_added'
            if r and r.done:
                status = 'done'

            recommend_date_str = (r.recommend_date.isoformat() if r else _add_age_offset(birthday, months_offset, d.days_offset).isoformat())

            groups.setdefault(label, []).append({
                'record_id': r.id if r else None,
                'vaccine_key': d.vaccine_key,
                'name': d.name,
                'dose_index': d.dose_index,
                'dose_total': d.dose_total,
                'fee_type': d.fee_type,
                'description': d.description or '',
                'recommend_date': recommend_date_str,
                'actual_date': r.actual_date.isoformat() if (r and r.actual_date) else None,
                'status': status,
                'price_min': d.price_min,
                'price_max': d.price_max
            })

        group_list = []
        for label in groups:
            group_list.append({
                'label': label,
                'items': groups[label]
            })

        def _group_sort_key(x):
            if x['label'] == '出生当天':
                return -1
            num = x['label'].replace('月龄', '')
            try:
                return float(num)
            except Exception:
                return 999

        group_list.sort(key=_group_sort_key)

        paid_candidates = []
        for d in defs:
            if d.fee_type != VaccineDefinition.FeeType.PAID:
                continue
            if record_map.get(d.vaccine_key):
                continue
            recommend_date = _add_age_offset(birthday, float(d.months_offset), d.days_offset)
            paid_candidates.append({
                'vaccine_key': d.vaccine_key,
                'name': d.name,
                'dose_index': d.dose_index,
                'dose_total': d.dose_total,
                'recommend_date': recommend_date.isoformat(),
                'price_min': d.price_min,
                'price_max': d.price_max
            })

        return Response({
            'code': 200,
            'msg': 'ok',
            'data': {
                'baby': {
                    'name': baby.name,
                    'birthday': baby.birthday.isoformat(),
                    'image': baby.image.url if baby.image else ''
                },
                'groups': group_list,
                'paid_candidates': paid_candidates
            }
        })


class VaccineToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        vaccine_key = request.data.get('vaccine_key')
        date_type = request.data.get('date_type')
        date_str = request.data.get('date')
        recommend_date_str = request.data.get('recommend_date')
        actual_date_str = request.data.get('actual_date')
        raw_done = request.data.get('done')

        if vaccine_key is None:
            return Response({'code': 400, 'msg': 'vaccine_key 必填', 'data': None})

        d = VaccineDefinition.objects.filter(vaccine_key=vaccine_key, is_active=True).first()
        if not d:
            return Response({'code': 400, 'msg': '未知疫苗', 'data': None})

        if date_type:
            if date_type not in ['recommend', 'actual']:
                return Response({'code': 400, 'msg': 'date_type 参数错误', 'data': None})

            if date_str is None:
                date_str = recommend_date_str if date_type == 'recommend' else actual_date_str
            if not date_str:
                return Response({'code': 400, 'msg': 'date 必填', 'data': None})

            try:
                new_date = date.fromisoformat(date_str)
            except Exception:
                return Response({'code': 400, 'msg': 'date 格式错误', 'data': None})

            record = _get_latest_record(request.user, vaccine_key)
            if not record and d.fee_type == BabyVaccineRecord.FeeType.PAID:
                return Response({'code': 400, 'msg': '请先添加自费疫苗', 'data': None})

            if date_type == 'recommend':
                if not record:
                    record = BabyVaccineRecord.objects.create(
                        user=request.user,
                        vaccine_key=vaccine_key,
                        name=d.name,
                        dose_index=d.dose_index,
                        dose_total=d.dose_total,
                        fee_type=d.fee_type,
                        description=d.description,
                        recommend_date=new_date,
                        done=False,
                        actual_date=None,
                        price_min=d.price_min,
                        price_max=d.price_max
                    )
                else:
                    record.recommend_date = new_date
                    record.save(update_fields=['recommend_date', 'updated_at'])
            else:
                if not record:
                    return Response({'code': 400, 'msg': '记录不存在', 'data': None})
                record.actual_date = new_date
                if not record.done:
                    record.done = True
                    record.save(update_fields=['done', 'actual_date', 'updated_at'])
                else:
                    record.save(update_fields=['actual_date', 'updated_at'])

            return Response({
                'code': 200,
                'msg': 'ok',
                'data': {
                    'record_id': record.id,
                    'done': record.done,
                    'recommend_date': record.recommend_date.isoformat(),
                    'actual_date': record.actual_date.isoformat() if record.actual_date else None
                }
            })

        if raw_done is None:
            return Response({'code': 400, 'msg': 'done 必填', 'data': None})

        done = raw_done if isinstance(raw_done, bool) else str(raw_done).lower() in ['1', 'true', 'yes']
        record = _get_latest_record(request.user, vaccine_key)
        if not record and d.fee_type == BabyVaccineRecord.FeeType.PAID:
            return Response({'code': 400, 'msg': '请先添加自费疫苗', 'data': None})

        if not record:
            baby = BabyInfo.objects.filter(user=request.user).first()
            if not baby or not baby.birthday:
                return Response({'code': 400, 'msg': '请先完善宝宝信息', 'data': None})
            if recommend_date_str:
                try:
                    recommend_date = date.fromisoformat(recommend_date_str)
                except Exception:
                    return Response({'code': 400, 'msg': 'recommend_date 格式错误', 'data': None})
            else:
                recommend_date = _add_age_offset(baby.birthday, float(d.months_offset), d.days_offset)
            record = BabyVaccineRecord.objects.create(
                user=request.user,
                vaccine_key=vaccine_key,
                name=d.name,
                dose_index=d.dose_index,
                dose_total=d.dose_total,
                fee_type=d.fee_type,
                description=d.description,
                recommend_date=recommend_date,
                done=False,
                actual_date=None,
                price_min=d.price_min,
                price_max=d.price_max
            )

        if done:
            if actual_date_str:
                try:
                    actual_date = date.fromisoformat(actual_date_str)
                except Exception:
                    return Response({'code': 400, 'msg': 'actual_date 格式错误', 'data': None})
            else:
                actual_date = record.actual_date or record.recommend_date
            record.done = True
            record.actual_date = actual_date
            record.save(update_fields=['done', 'actual_date', 'updated_at'])
        else:
            record.done = False
            record.actual_date = None
            record.save(update_fields=['done', 'actual_date', 'updated_at'])

        return Response({
            'code': 200,
            'msg': 'ok',
            'data': {
                'record_id': record.id,
                'done': record.done,
                'recommend_date': record.recommend_date.isoformat(),
                'actual_date': record.actual_date.isoformat() if record.actual_date else None
            }
        })


class VaccineAddPaidView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        vaccine_key = request.data.get('vaccine_key')
        recommend_date_str = request.data.get('recommend_date')
        if vaccine_key is None or recommend_date_str is None:
            return Response({'code': 400, 'msg': 'vaccine_key/recommend_date 必填', 'data': None})

        try:
            recommend_date = date.fromisoformat(recommend_date_str)
        except Exception:
            return Response({'code': 400, 'msg': 'recommend_date 格式错误', 'data': None})

        d = VaccineDefinition.objects.filter(vaccine_key=vaccine_key, is_active=True).first()
        if not d:
            return Response({'code': 400, 'msg': '未知疫苗', 'data': None})
        if d.fee_type != BabyVaccineRecord.FeeType.PAID:
            return Response({'code': 400, 'msg': '该疫苗不是自费疫苗', 'data': None})

        record = BabyVaccineRecord.objects.filter(
            user=request.user,
            vaccine_key=vaccine_key,
            recommend_date=recommend_date
        ).first()
        if record:
            return Response({'code': 200, 'msg': 'ok', 'data': {'record_id': record.id}})

        record = BabyVaccineRecord.objects.create(
            user=request.user,
            vaccine_key=vaccine_key,
            name=d.name,
            dose_index=d.dose_index,
            dose_total=d.dose_total,
            fee_type=d.fee_type,
            description=d.description,
            recommend_date=recommend_date,
            done=False,
            actual_date=None,
            price_min=d.price_min,
            price_max=d.price_max
        )
        return Response({'code': 200, 'msg': 'ok', 'data': {'record_id': record.id}})
