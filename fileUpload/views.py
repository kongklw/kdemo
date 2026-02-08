import os.path
from uuid import uuid1

from rest_framework.views import APIView
from rest_framework.response import Response
from kdemo.settings import MEDIA_ROOT


# Create your views here.


from rest_framework.permissions import IsAuthenticated
from .models import File

class CommonFileUpload(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        if not file:
             return Response({'code': 400, 'msg': 'No file uploaded', 'data': None})
        
        # 保存文件记录到数据库并关联用户
        # FileField 会自动处理文件保存到 MEDIA_ROOT/files/... (由 user_directory_path 定义)
        file_obj = File(user=request.user, file=file, upload_method='upload')
        file_obj.save()
        
        # 获取相对路径或URL
        # 注意：这里假设前端需要的是相对路径或完整URL，根据 FileField 的 url 属性
        file_url = file_obj.file.url
        name = file_obj.file.name # 包含路径的文件名

        return Response({'code': 200, 'data': {'name': name, 'url': file_url}, 'msg': 'ok'})

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
