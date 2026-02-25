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
from utils import alibaba_client
from utils.chatApp import obtain_app
from kdemo.settings import MEDIA_ROOT
from langchain_core.messages import HumanMessage
import concurrent.futures

logger = logging.getLogger(__name__)


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

        objs = BabyExpense(user=user, order_time=order_time, name=name, amount=amount, tag=tag,
                           expense_type=expense_type)
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
    #  读取本地文件，并编码为 BASE64 格式
    def encode_image(image_path):
        image_type = image_path[image_path.rindex('.') + 1:].lower()
        with open(image_path, "rb") as image_file:
            return image_type, base64.b64encode(image_file.read()).decode("utf-8")

    @classmethod
    def process_image_msg(cls, path, user):
        thread_id = uuid.uuid1()
        # Fix: Normalize path separators and join correctly
        path = path.replace('\\', '/')
        
        # Robustness check: if file not found at path, try looking in 'files/' subdirectory
        # This handles cases where path might be just a filename but file is in files/
        image_path = os.path.join(MEDIA_ROOT, path)
        if not os.path.exists(image_path):
            alt_path = os.path.join(MEDIA_ROOT, 'files', os.path.basename(path))
            if os.path.exists(alt_path):
                # Update path to include files/ prefix
                path = 'files/' + os.path.basename(path)
                image_path = alt_path

        image_type, base64_image = cls.encode_image(image_path)
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
            print(f"Both tasks have completed now: {item.result()}")

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
                    print('%r generated an exception: %s' % (url, exc))
                else:
                    print('%r page is %d bytes' % (url, len(data)))

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
        print('total wast time are :', end - start)
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
            filter_kwargs['name__contains'] = params.get('name')

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

        serializer = BabyExpenseSerializer(page_data, many=True)

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
