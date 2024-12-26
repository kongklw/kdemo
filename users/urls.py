from django.urls import path, include
from rest_framework_simplejwt.views import TokenBlacklistView
from rest_framework_simplejwt.views import token_obtain_pair

from . import views

urlpatterns = [
    path('signin', views.UserView.as_view()),
    path('login', views.LoginView.as_view()),
    path('info', views.UserInfo.as_view()),
    path('logout', views.Logout.as_view()),
    # path('logout', TokenBlacklistView.as_view(), name='token_blacklist'),

]
