from django.urls import path, include
from rest_framework_simplejwt.views import TokenBlacklistView
from . import views

urlpatterns = [
    path('login', views.LoginView.as_view()),
    path('info', views.UserInfo.as_view()),
    path('logout', views.Logout.as_view()),
    # path('logout', TokenBlacklistView.as_view(), name='token_blacklist'),

]
