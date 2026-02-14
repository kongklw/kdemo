from xml.dom.minidom import ProcessingInstruction

from django.shortcuts import render
from rest_framework.decorators import authentication_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib import auth
from .models import User
from rest_framework.generics import CreateAPIView
from .serializers import CreateUserSerializer


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# class TokenError(Exception):
#     pass

class UserView(APIView):
    # serializer_class = CreateUserSerializer
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            print('----------', data)
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            phone = data.get('phone')

            user = User.objects.create_user(username=username, email=email, password=password, phone=phone)
            user.save()

            return Response({'code': 200, 'msg': 'ok', 'data': None})
        except Exception as exc:
            return Response({'code': 205, 'msg': str(exc), 'data': None})

        # serializer = CreateUserSerializer(data=data)
        # if serializer.is_valid():
        #     print('验证通过')
        #     serializer.save()
        # else:
        #     print('验证失败')
        #     print(str(serializer.errors))
        #     return Response({'code': 205, 'msg': 'failed', 'data': None})
        # return Response({'code': 200, 'msg': 'ok', 'data': None})


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            username = data.get("username") # 这里前端传过来的是手机号，字段名还是username
            password = data.get("password")
            
            # 1. 先尝试用 username 直接登录 (兼容原有逻辑)
            user = authenticate(username=username, password=password)
            
            # 2. 如果失败，尝试用手机号登录
            if user is None:
                try:
                    user_obj = User.objects.get(phone=username)
                    # 找到用户后，再验证密码
                    if user_obj.check_password(password):
                        user = user_obj
                except User.DoesNotExist:
                    pass
            
            print(user)

            if user is not None:
                # A backend authenticated the credentials
                token_data = get_tokens_for_user(user=user)

                access = token_data.get("access")
                response = {"code": 200, "data": {"token": access}, "msg": "success"}

            else:
                # No backend authenticated the credentials

                response = {"code": 205, "data": None, "msg": '账号或密码错误'}
            return Response(response)
        except Exception as exc:
            response = {"code": 205, "data": None, "msg": str(exc)}
            return Response(response)


class UserInfo(APIView):
    authentication_classes = [JWTAuthentication]

    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            params = request.query_params
            token = params.get("token")
            jwt_auth = JWTAuthentication()
            payload: AccessToken = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(payload)
            id = user.id
            username = user.username
            user_info = {
                "roles": ['admin'],
                "introduction": 'I am a super administrator',
                "avatar": 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif',
                "name": 'Super Admin'

            }

            response = {"code": 200, "data": user_info, "msg": "ok"}
            return Response(response)
        except Exception as exc:
            response = {"code": 205, "data": None, "msg": str(exc)}

            return Response(response)


class Logout(APIView):
    # permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        try:
            res = auth.logout(request)
            print('调用logout  ', res)
            return Response({"code": 200, "data": "ok", "msg": "ok"})
        except Exception as exc:

            return Response({"code": 205, "data": None, "msg": str(exc)})
