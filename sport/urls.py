from django.urls import path, include
from . import views

urlpatterns = [
    path('add', views.SportView.as_view()),
    path('list', views.SportList.as_view()),
]
