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


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# class TokenError(Exception):
#     pass


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            username = data.get("username")
            password = data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                # A backend authenticated the credentials
                token_data = get_tokens_for_user(user=user)

                access = token_data.get("access")
                response = {"code": 200, "data": {"token": access}, "msg": "success"}

            else:
                # No backend authenticated the credentials

                response = {"code": 205, "data": None, "msg": "error"}
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
            return Response({"code": 200, "data": "ok", "msg": "ok"})
        except Exception as exc:

            return Response({"code": 205, "data": None, "msg": str(exc)})
