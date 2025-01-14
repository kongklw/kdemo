from django.urls import path, include
from . import views

urlpatterns = [

    path('ask', views.OpenAIView.as_view()),

]
