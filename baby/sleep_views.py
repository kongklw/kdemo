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
        try:
            page = int(params.get("currentPage", params.get("page_num", 1)))
            page_size = int(params.get("pageSize", params.get("page_size", 10)))
        except (ValueError, TypeError):
            page = 1
            page_size = 10

        start_index = (page - 1) * page_size
        end_index = page * page_size
        
        queryset = SleepLog.objects.filter(user=user, sleep_time__date=date).order_by('-sleep_time')
        count = queryset.count()
        objs = queryset[start_index:end_index]
        
        serializer = SleepLogSerializer(objs, many=True)
        return Response({'code': 200, 'data': {'results': serializer.data, 'count': count}, 'msg': 'ok'})
