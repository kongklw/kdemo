from django.urls import path, include
from rest_framework_simplejwt.views import TokenBlacklistView
from . import views

urlpatterns = [
    path('pods', views.Pos.as_view()),

]
