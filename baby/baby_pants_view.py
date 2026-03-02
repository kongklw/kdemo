import json
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BabyDiapers, PantsBrandModel
from .serializers import BabyDiapersSerializer, PantsBrandSerializer
from custom import MyModelViewSet

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


from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class BabyPantsView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        use_date = params.get("use_date")
        
        queryset = BabyDiapers.objects.filter(user=user.id).order_by("-use_date")
        
        if use_date and use_date != 'null' and use_date != 'undefined':
            queryset = queryset.filter(use_date__date=use_date)
            
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = BabyDiapersSerializer(page, many=True)
            result_data = serializer.data
        else:
            serializer = BabyDiapersSerializer(queryset, many=True)
            result_data = serializer.data

        status_list = []

        for item in result_data:
            status = item.get("tabActiveName")
            item_dict = {"id": item.get("id"), "status": statusMap.get(status), "describe": item.get("describe"),
                         "use_date": item.get("use_date")}
            if status == "peeing":
                item_dict["peeing"] = item.get("peeing_color")
            elif status == "stool":
                item_dict["stool"] = str(item.get("stool_color") or "") + str(item.get("stool_shape") or "")
            elif status == "peeing-stool":
                item_dict["peeing"] = item.get("peeing_color")
                item_dict["stool"] = str(item.get("stool_color") or "") + str(item.get("stool_shape") or "")
            else:
                pass

            status_list.append(item_dict)
            
        return Response({"code": 200, "data": {"results": status_list, "count": queryset.count()},
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
            stool_shape_list = data.get("stool_shape_list")
            if stool_shape_list:
                stool_shape = "#".join(stool_shape_list)
            else:
                stool_shape = ""
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
            logger.exception("BabyPants create error")
            return Response({'code': 205, 'msg': str(exc), 'data': None})

    def delete(self, request, *args, **kwargs):

        data = request.data
        id = data.get("id")
        obj = BabyDiapers.objects.get(id=id)
        obj.delete()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})


class BrandPantsView(MyModelViewSet):

    def get(self, request, *args, **kwargs):

        user = request.user
        objs = PantsBrandModel.objects.filter(user=user.id)
        serializer = PantsBrandSerializer(objs, many=True)
        # Serializer with instance argument doesn't need is_valid()
        data = serializer.data
        response = {'code': 200, "data": data, "msg": "ok"}

        return Response(response)

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        brand_name = data.get("brand_name")

        obj = PantsBrandModel(user=user.id, brand_name=brand_name)
        obj.save()

        return Response(response={'code': 200, "data": None, "msg": "ok"})


