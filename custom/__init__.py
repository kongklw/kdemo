from rest_framework import viewsets
from rest_framework.response import Response
'''
https://blog.csdn.net/lspjuzi/article/details/136556095
'''

class APIResponse(Response):
    def __init__(self, code=200, msg="success", data=None, status=None, headers=None, **kwargs):
        dic = {'code': code, 'msg': msg}
        if data:
            dic = {'code': code, 'msg': msg, 'data': data}
        dic.update(kwargs)
        super().__init__(data=dic, status=status, headers=headers)


class MyModelViewSet(viewsets.ModelViewSet):

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return APIResponse(data=response.data)

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        return APIResponse(status=response.status_code)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return APIResponse(data=response.data)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)

        return APIResponse(data=response.data)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return APIResponse(data=response.data, status=response.status_code, headers=response.headers)
    # def list(self, request, *args, **kwargs):
    #     queryset = self.filter_queryset(self.get_queryset())
    #
    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         # return self.get_paginated_response(serializer.data)
    #         return Response({"code": 200, "msg": "success", "data": serializer.data})
    #
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response({"code": 200, "msg": "success", "data": serializer.data})
    #
    # def update(self, request, *args, **kwargs):
    #     partial = kwargs.pop('partial', False)
    #     instance = self.get_object()
    #     serializer = self.get_serializer(instance, data=request.data, partial=partial)
    #     # serializer.is_valid(raise_exception=True)
    #     is_valid = serializer.is_valid(raise_exception=False)
    #     if not is_valid:
    #         return Response({"code": 205, "msg": serializer.errors, "data": None})
    #
    #     self.perform_update(serializer)
    #
    #     if getattr(instance, '_prefetched_objects_cache', None):
    #         # If 'prefetch_related' has been applied to a queryset, we need to
    #         # forcibly invalidate the prefetch cache on the instance.
    #         instance._prefetched_objects_cache = {}
    #
    #     # return Response(serializer.data)
    #
    #     return Response({"code": 200, "msg": "success", "data": serializer.data})
