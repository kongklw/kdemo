from django.urls import path, include
from . import views, temperature_views,baby_pants_view,dashboard_views
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
    path('dashboard', dashboard_views.DashBoardView.as_view()),
    path('todo', views.TodoListView.as_view()),
    path('feed', views.FeedMilkView.as_view()),
    path('temperature', temperature_views.TemperatureView.as_view()),
    path('pants', baby_pants_view.BabyPantsView.as_view()),
    path('line_chart', views.LineChartView.as_view()),
    path('expense_list', views.ExpenseListView.as_view()),
    path('expense', views.ExpenseView.as_view()),
    path('batch_expense', views.BatchExpenseView.as_view()),
    path('batch_delete_expense', views.BatchDeleteExpenseView.as_view()),
    path('sleep_list', views.SleepListView.as_view()),
    path('sleep', views.SleepView.as_view()),
]
