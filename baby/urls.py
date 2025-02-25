from django.urls import path, include
from . import (views, temperature_views, baby_pants_view, todo_views,
               dashboard_views, sleep_views, expense_views, growing_blog_view,
               breast_feed_views)
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

    # growing moments blog
    path('growing', growing_blog_view.GrowingBlogView.as_view()),
    path('ai_gen', growing_blog_view.AIGenView.as_view()),

    # todo
    path('todo', todo_views.TodoListView.as_view()),
    path('todo_table', todo_views.TodoTableView.as_view()),

    # feed
    path('feed', breast_feed_views.FeedMilkView.as_view()),
    path('feed_chart', breast_feed_views.FeedChart.as_view()),

    # temperature
    path('temperature', temperature_views.TemperatureView.as_view()),

    # pants
    path('pants', baby_pants_view.BabyPantsView.as_view()),
    path('line_chart', views.LineChartView.as_view()),

    # expense
    path('expense_list', expense_views.ExpenseListView.as_view()),
    path('expense', expense_views.ExpenseView.as_view()),
    path('batch_expense', expense_views.BatchExpenseView.as_view()),
    path('batch_delete_expense', expense_views.BatchDeleteExpenseView.as_view()),

    # sleep
    path('sleep_list', sleep_views.SleepListView.as_view()),
    path('sleep', sleep_views.SleepView.as_view()),
]
