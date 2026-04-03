from django.urls import path, include
from . import (views, temperature_views, baby_pants_view, todo_views,
               dashboard_views, sleep_views, expense_views, growing_blog_view,
               breast_feed_views, baby_info_views, album_views, body_views, vaccine_views, period_views)

urlpatterns = [

    path('info', baby_info_views.BabyInfoView.as_view()),
    path('dashboard', dashboard_views.DashBoardView.as_view()),

    # growing moments blog
    path('growing', growing_blog_view.GrowingBlogView.as_view()),
    path('ai_gen', growing_blog_view.AIGenView.as_view()),

    # todo
    path('todo', todo_views.TodoListView.as_view()),
    path('todo_table', todo_views.TodoTableView.as_view()),
    path('daily_habit', todo_views.DailyHabitView.as_view()),

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
    path('expense_tags', expense_views.ExpenseTagView.as_view()),

    # sleep
    path('sleep_list', sleep_views.SleepListView.as_view()),
    path('sleep', sleep_views.SleepView.as_view()),

    # baby album
    path('albums/', album_views.BabyAlbumListCreateView.as_view()),
    path('albums/<int:pk>/', album_views.BabyAlbumDetailView.as_view()),
    path('albums/video/<str:stream_id>/playback', album_views.AlbumVideoPlaybackInfoView.as_view()),
    path('albums/video/<str:stream_id>/hls/<path:playlist_path>', album_views.AlbumVideoHlsView.as_view()),
    path('albums/video/<str:stream_id>/dash/<path:dash_path>', album_views.AlbumVideoDashView.as_view()),

    # body metrics
    path('growth_records/', body_views.GrowthRecordListCreateView.as_view()),
    path('growth_records/<int:pk>/', body_views.GrowthRecordDetailView.as_view()),

    # vaccine schedule
    path('vaccines/schedule/', vaccine_views.VaccineScheduleView.as_view()),
    path('vaccines/toggle/', vaccine_views.VaccineToggleView.as_view()),
    path('vaccines/add_paid/', vaccine_views.VaccineAddPaidView.as_view()),

    # period tracker
    path('period/overview', period_views.PeriodOverviewView.as_view()),
    path('period/log', period_views.PeriodLogView.as_view()),
    path('period/settings', period_views.PeriodSettingsView.as_view()),

    path('birthday', views.BirthdayView.as_view()),
]
