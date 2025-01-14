from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

# babyRouter = DefaultRouter()
#
# babyRouter.register(r"info", views.BabyInfoViewSet)
# babyRouter.register(r"feed", views.FeedMilkView,basename='feed')
# babyRouter.register(r"sleep", views.SleepLogViewSet)
# babyRouter.register(r"diapers", views.BabyDiapersViewSet)
# babyRouter.register(r"expense", views.BabyExpenseViewSet)

urlpatterns = [
    # path('info', views.BabyInfoViewSet),
    path('todo', views.TodoListView.as_view()),
    path('feed', views.FeedMilkView.as_view()),
    path('temperature', views.TemperatureView.as_view()),
    path('pants', views.BabyPantsView.as_view()),
    path('line_chart', views.LineChartView.as_view()),
    path('expense_list', views.ExpenseListView.as_view()),
    path('expense', views.ExpenseView.as_view()),
]
