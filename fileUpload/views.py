import os.path
from rest_framework.views import APIView
from rest_framework.response import Response
from kdemo.settings import MEDIA_ROOT


# Create your views here.


class CommonFileUpload(APIView):

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        name = file.name
        path = os.path.join(MEDIA_ROOT + name)

        with open(path, 'wb') as f:
            for content in file.chunks():
                f.write(content)

        return Response({'code': 200, 'data': {'name': name, 'url': 'https://www.baidu.com/haha'}, 'msg': 'ok'})

        # files = request.FILES.getlist("file", None)
        # file_list = []
        # for file in files:
        #
        #     name = file.name
        #     file_list.append(name)
        #     path = os.path.join(MEDIA_ROOT + name)
        #
        #     with open(path, 'wb') as f:
        #         for content in file.chunks():
        #             f.write(content)
        #
        # return Response({'code': 200, 'data': file_list, 'msg': 'ok'})
