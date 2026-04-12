from django.urls import path, include
from . import views


urlpatterns = [

    # period tracker
    path("common/", views.CommonView.as_view(), name='common rag view'),

]
