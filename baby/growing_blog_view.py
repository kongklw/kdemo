import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import GrowingBlogModel
from .serializers import GrowingBlogSerializer
from utils.chatApp import obtain_app, model

logger = logging.getLogger(__name__)


class AIGenView(APIView):

    def post(self, request, *args, **kwargs):
        try:

            data = request.data
            content = data.get("content")

            app = obtain_app(type="json", need_mem=False)
            language = "chinese"

            content = f"""根据下面的内容，写一个带有标题不超过200字的文章。\
                        ```{content}```\
                        结果以json格式返回，key 为 title, content
            """

            messages = [

                {"role": "user", "content": content}
            ]
            output = app.invoke({"messages": messages, "language": language})
            msg = output["messages"][-1].content

            return Response({'code': 200, 'msg': 'ok', 'data': json.loads(msg)})

        except Exception as exc:

            return Response({'code': 205, 'msg': str(exc), 'data': None})


class GrowingBlogView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user

        objs = GrowingBlogModel.objects.filter(user=user).order_by('-id')
        serializer = GrowingBlogSerializer(objs, many=True)

        return Response({"code": 200, "data": serializer.data,
                         "msg": "fetch all success"})

    def post(self, request, *args, **kwargs):
        try:
            print(request.data)

            serializer = GrowingBlogSerializer(data=request.data, context={"request": request})
            if serializer.is_valid():
                serializer.save()
            else:
                print(serializer.errors)
                return Response({'code': 205, 'msg': str(serializer.errors), 'data': None})

            return Response({'code': 200, 'msg': 'ok', 'data': None})

        except Exception as exc:

            return Response({'code': 205, 'msg': str(exc), 'data': None})

    def delete(self, request, *args, **kwargs):
        data = request.data
        id = data.get("id")
        obj = GrowingBlogModel.objects.get(id=id)
        obj.delete()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})
