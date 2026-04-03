import json
import logging
import base64
import os, uuid
import time
import asyncio
from rest_framework.views import APIView
from rest_framework.response import Response
from custom import MyModelViewSet
from .models import BabyInfo, FeedMilk, SleepLog, BabyDiapers, BabyExpense, Temperature, TodoList, ExpenseTag
from .serializers import BabyInfoSerializer, FeedMilkSerializer, SleepLogSerializer, BabyDiapersSerializer, \
    BabyExpenseSerializer, TemperatureSerializer, TodoListSerializer
from utils import convert_seconds, convert_string_datetime, convert_string_date
from datetime import datetime, timedelta, date
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Sum
from zoneinfo import ZoneInfo
from decimal import Decimal, getcontext
from kdemo.settings import MEDIA_ROOT
import concurrent.futures
from django.conf import settings
import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

_S3_CLIENT = None


def _get_s3_client():
    global _S3_CLIENT
    if _S3_CLIENT is not None:
        return _S3_CLIENT
    verify = True
    if hasattr(settings, 'MINIO_VERIFY_SSL'):
        verify = bool(settings.MINIO_VERIFY_SSL)
    _S3_CLIENT = boto3.client(
        's3',
        aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
        aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
        endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
        region_name=getattr(settings, 'AWS_S3_REGION_NAME', None),
        verify=verify,
        config=Config(
            signature_version=getattr(settings, 'AWS_S3_SIGNATURE_VERSION', 's3v4'),
            s3={'addressing_style': getattr(settings, 'AWS_S3_ADDRESSING_STYLE', 'path')},
        ),
    )
    return _S3_CLIENT


def _guess_image_type_from_path(path: str) -> str:
    ext = os.path.splitext(path or '')[1].lower().lstrip('.')
    return ext or 'jpeg'


def _read_media_bytes(path: str) -> tuple[str, bytes]:
    norm = (path or '').replace('\\', '/').lstrip('/')
    image_type = _guess_image_type_from_path(norm)

    if getattr(settings, 'USE_S3_MEDIA', False):
        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        if bucket:
            s3 = _get_s3_client()
            tried = [norm]
            if norm and not norm.startswith('files/'):
                tried.append(f'files/{os.path.basename(norm)}')
            for key in tried:
                try:
                    obj = s3.get_object(Bucket=bucket, Key=key)
                    body = obj.get('Body')
                    data = body.read() if body else b''
                    if data:
                        return _guess_image_type_from_path(key), data
                except Exception:
                    continue

    image_path = os.path.join(MEDIA_ROOT, norm)
    if not os.path.exists(image_path):
        alt_path = os.path.join(MEDIA_ROOT, 'files', os.path.basename(norm))
        if os.path.exists(alt_path):
            image_path = alt_path
            norm = f'files/{os.path.basename(norm)}'

    with open(image_path, 'rb') as f:
        return _guess_image_type_from_path(norm), f.read()


class ExpenseView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user

        create_time = datetime.now().date().strftime('%Y-%m-%d')

        objs = TodoList.objects.filter(user=user, create_time=create_time)
        serializer = TodoListSerializer(objs, many=True)

        return Response({'code': 200, 'data': serializer.data, 'msg': 'ok'})

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        order_time = data.get("order_time")
        name = data.get("name")
        amount = data.get("amount")
        tag = data.get("tag")
        expense_type = data.get("expense_type", "expense")
        image_url = data.get("image_url")

        objs = BabyExpense(user=user, order_time=order_time, name=name, amount=amount, tag=tag,
                           expense_type=expense_type, image_url=image_url)
        objs.save()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})

    def put(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        pk = data.get("id")
        if not pk:
            return Response({'code': 400, 'msg': 'id is required'})

        try:
            obj = BabyExpense.objects.get(id=pk, user=user)
        except BabyExpense.DoesNotExist:
            return Response({'code': 404, 'msg': 'not found'})

        obj.order_time = data.get("order_time", obj.order_time)
        obj.name = data.get("name", obj.name)
        obj.amount = data.get("amount", obj.amount)
        obj.tag = data.get("tag", obj.tag)
        obj.expense_type = data.get("expense_type", obj.expense_type)
        obj.image_url = data.get("image_url", obj.image_url)
        obj.save()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})


class BatchDeleteExpenseView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        ids = data.get("ids")

        objs = BabyExpense.objects.filter(user=user, id__in=ids)
        objs.delete()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})


class BatchExpenseView(APIView):

    @staticmethod
    def encode_image_bytes(image_type: str, raw_bytes: bytes):
        return image_type, base64.b64encode(raw_bytes).decode("utf-8")

    @classmethod
    def process_image_msg(cls, path, user):
        from utils.chatApp import obtain_app
        from langchain_core.messages import HumanMessage

        thread_id = uuid.uuid1()
        path = (path or '').replace('\\', '/')
        image_type, raw = _read_media_bytes(path)
        image_type, base64_image = cls.encode_image_bytes(image_type, raw)
        input_message = [HumanMessage(
            content=[

                {"type": "text",
                 "text": "describe product name if there are multiple merge lines,product category,pay amount ignore money units and pay time"},
                # {"type": "text", "text": "Return a JSON object with {'product_name':product_name,'order_amount':order_amount,'product_categories':product_categories,'order_time':order_time}"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{image_type};base64,{base64_image}"},
                },
            ]
        )]

        app = obtain_app(type='json')
        language = "english"
        config = {"configurable": {"thread_id": thread_id}}
        output = app.invoke({"messages": input_message, "language": language}, config)
        modelContent = json.loads(output["messages"][-1].content)

        res_data = {'image_url': path}
        for key, value in modelContent.items():
            if key == 'product_name':
                res_data['name'] = str(value)
            elif key == 'pay_time':
                res_data['order_time'] = value
            elif key == 'pay_amount':
                res_data['amount'] = Decimal(value)
            elif key == 'product_category':
                res_data['tag'] = str(value)
            else:
                pass

        objs = BabyExpense(user=user, order_time=res_data.get('order_time'), name=res_data.get('name'),
                           amount=res_data.get('amount'), tag=res_data.get('tag'),
                           image_url=res_data.get('image_url'))
        objs.save()

        return f'ok {thread_id}'

    @staticmethod
    async def process(cls, request):
        user = request.user
        data = request.data
        fileList = data['fileList']
        task_list = []
        async with asyncio.TaskGroup() as tg:
            for item in fileList:
                path = item.get('name')
                task = tg.create_task(cls.process_image_msg(path, user))
                task_list.append(task)

        for item in task_list:
            logger.debug("Expense image task done: %s", item.result())

    def post(self, request, *args, **kwargs):
        start = time.time()

        user = request.user
        data = request.data
        fileList = data['fileList']

        # 我们可以使用一个 with 语句来确保线程被迅速清理
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # 开始加载操作并以每个 Future 对象的 URL 对其进行标记
            future_to_llm = {executor.submit(self.process_image_msg, item.get('name'), user): item for item in fileList}
            for future in concurrent.futures.as_completed(future_to_llm):
                url = future_to_llm[future]
                try:
                    data = future.result()

                except Exception as exc:
                    logger.exception("Expense image task error: %s", url)
                else:
                    logger.debug("Expense image task ok: %s", url)

        # task_list = []
        # async with asyncio.TaskGroup() as tg:
        #     for item in fileList:
        #         path = item.get('name')
        #         task = tg.create_task(self.process_image_msg(path, user))
        #         task_list.append(task)
        #
        # for item in task_list:
        #     print(f"Both tasks have completed now: {item.result()}")

        # asyncio.run(self.process(request))

        end = time.time()
        logger.info("ExpenseView post total time: %.3fs", end - start)
        return Response({'code': 200, 'data': 'haha success', 'msg': 'ok'})


class ExpenseListView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        params = request.data

        page_size = params.get('page_size', 20)
        page_num = params.get('page_num', 1)

        # Build filter query
        filter_kwargs = {'user': user}

        if params.get('name'):
            filter_kwargs['name__icontains'] = params.get('name')
        
        # Filter by expense type (income/expense)
        if params.get('expense_type') and params.get('expense_type') in ['income', 'expense']:
            filter_kwargs['expense_type'] = params.get('expense_type')

        if params.get('monthrange'):
            start_date = params.get('monthrange')[0]
            end_date = params.get('monthrange')[1]
            filter_kwargs['order_time__range'] = (start_date + ' 00:00:00', end_date + ' 23:59:59')

        queryset = BabyExpense.objects.filter(**filter_kwargs).order_by('-order_time')

        # Calculate range statistics (based on current filters)
        range_income = queryset.filter(expense_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
        range_expense = queryset.filter(expense_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0

        # Calculate total statistics (all data for user)
        all_queryset = BabyExpense.objects.filter(user=user)
        all_income = all_queryset.filter(expense_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
        all_expense = all_queryset.filter(expense_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Paginate
        start = (page_num - 1) * page_size
        end = start + page_size
        page_data = queryset[start:end]
        total = queryset.count()

        serializer = BabyExpenseSerializer(page_data, many=True, context={'request': request})

        return Response({
            'code': 200,
            'data': {
                'list': serializer.data,
                'total': total,
                'all_income': all_income,
                'all_expense': all_expense,
                'range_income': range_income,
                'range_expense': range_expense
            },
            'msg': 'ok'
        })


class ExpenseTagView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        tags = ExpenseTag.objects.filter(user=user).values_list('name', flat=True)
        return Response({'code': 200, 'data': list(tags), 'msg': 'ok'})

    def post(self, request, *args, **kwargs):
        user = request.user
        name = request.data.get("name")
        if not name:
            return Response({'code': 400, 'msg': 'name is required'})
        
        # Check duplicate
        if ExpenseTag.objects.filter(user=user, name=name).exists():
            return Response({'code': 400, 'msg': 'Tag already exists'})
            
        ExpenseTag.objects.create(user=user, name=name)
        return Response({'code': 200, 'msg': 'ok'})
