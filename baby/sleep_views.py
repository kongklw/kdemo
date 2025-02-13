import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import SleepLog
from .serializers import SleepLogSerializer

logger = logging.getLogger(__name__)


class SleepView(APIView):

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        """
        {'sleep_time': '2025-02-13T13:50:25.000Z', 'status': '醒着', 'describe': ''}

        """

        sleep_time = data.get("sleep_time")
        status = data.get("status")
        describe = data.get("describe")
        duration = data.get("duration")

        objs = SleepLog(user=user, sleep_time=sleep_time, status=status, describe=describe, duration=duration)
        objs.save()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})


class SleepListView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        params = request.data

        date = params.get("date")
        page = params.get("currentPage")
        page_size = params.get("pageSize")

        objs = SleepLog.objects.filter(user=user, sleep_time__date=date).order_by('-sleep_time')[
               (page - 1) * page_size:page * page_size]
        serializer = SleepLogSerializer(objs, many=True)
        return Response({'code': 200, 'data': serializer.data, 'msg': 'ok'})
