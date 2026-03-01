import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import TodoList, DailyHabit
from .serializers import TodoListSerializer, TodoTableSerializer, DailyHabitSerializer
from datetime import datetime, timedelta, date
from django.db.models import Count
import pandas as pd
from itertools import groupby
import os

logger = logging.getLogger(__name__)


def init_items(user):
    # Check if user has any DailyHabits defined (active or inactive)
    # This prevents re-initializing defaults if user intentionally deleted all habits
    has_habits = DailyHabit.objects.filter(user=user).exists()
    
    if not has_habits:
        # Initialize default habits if none exist at all
        default_habits = [
            {"text": "补充AD", "icon": "medication"},
            {"text": "补充钙/铁", "icon": "cube"},
            {"text": "补充益生菌", "icon": "flower-o"},
            {"text": "观察大便", "icon": "smile-o"},
            {"text": "洗澡抚触", "icon": "hot-o"},
            {"text": "亲子阅读", "icon": "book"},
            {"text": "趴卧练习", "icon": "like-o"},
            {"text": "户外活动", "icon": "location-o"},
        ]
        
        for h in default_habits:
            DailyHabit.objects.create(
                user=user, 
                text=h["text"], 
                icon=h["icon"]
            )
    
    # Get active habits to create today's todos
    active_habits = DailyHabit.objects.filter(user=user, is_active=True)
    
    # Create today's todo items from habits
    for habit in active_habits:
        TodoList.objects.create(
            user=user, 
            text=habit.text, 
            is_daily=True, 
            icon=habit.icon
        )


class TodoTableView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        objs = TodoList.objects.filter(user=user, create_time__gte=start_date, create_time__lte=end_date).values(
            "create_time", "text", "done", "is_daily", "icon")

        serializer = TodoTableSerializer(objs, many=True)
        data = serializer.data
        grouped = groupby(data, key=lambda x: x["create_time"])

        aim_list = []
        for key, group in grouped:
            aim_list.append({"date": key, "date_items": list(group)})

        aim_list.reverse()

        return Response({'code': 200, 'data': aim_list, 'msg': 'ok'})


class TodoListView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        today = date.today().strftime('%Y-%m-%d')

        objs = TodoList.objects.filter(user=user, create_time__gte=start_date, create_time__lte=end_date)
        
        # If querying for today and list is empty, initialize from habits
        if (start_date == end_date) and (start_date == today) and len(objs) == 0:
            init_items(user)
            objs = TodoList.objects.filter(user=user, create_time__gte=start_date, create_time__lte=end_date)
            
        serializer = TodoListSerializer(objs, many=True)
        return Response({'code': 200, 'data': serializer.data, 'msg': 'ok'})

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        text = data.get("text")
        done = data.get("done", False)
        is_daily = data.get("is_daily", False)
        icon = data.get("icon", "")

        obj = TodoList(user=user, text=text, done=done, is_daily=is_daily, icon=icon)
        obj.save()
        return Response({'code': 200, 'data': None, 'msg': 'ok'})

    def put(self, request, *args, **kwargs):
        data = request.data
        task_id = data.get("id")
        try:
            obj = TodoList.objects.get(id=task_id, user=request.user)
            serializer = TodoListSerializer(obj, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
            return Response({'code': 200, 'data': None, 'msg': 'ok'})
        except TodoList.DoesNotExist:
            return Response({'code': 404, 'msg': 'Todo not found'})

    def delete(self, request, *args, **kwargs):
        data = request.data
        task_id = data.get("id")
        try:
            obj = TodoList.objects.get(id=task_id, user=request.user)
            obj.delete()
            return Response({'code': 200, 'data': None, 'msg': 'ok'})
        except TodoList.DoesNotExist:
             return Response({'code': 404, 'msg': 'Todo not found'})

class DailyHabitView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        habits = DailyHabit.objects.filter(user=user, is_active=True)
        serializer = DailyHabitSerializer(habits, many=True)
        return Response({'code': 200, 'data': serializer.data, 'msg': 'ok'})

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        data['user'] = user.id
        serializer = DailyHabitSerializer(data=data)
        if serializer.is_valid():
            habit = serializer.save(user=user)
            # Create today's todo item
            TodoList.objects.create(
                user=user,
                text=habit.text,
                is_daily=True,
                icon=habit.icon
            )
            return Response({'code': 200, 'msg': 'Habit added'})
        return Response({'code': 400, 'msg': serializer.errors})

    def put(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        habit_id = data.get('id')
        try:
            habit = DailyHabit.objects.get(id=habit_id, user=user)
        except DailyHabit.DoesNotExist:
            return Response({'code': 404, 'msg': 'Habit not found'})
        
        old_text = habit.text
        
        serializer = DailyHabitSerializer(habit, data=data, partial=True)
        if serializer.is_valid():
            habit = serializer.save()
            
            today = date.today()
            
            # If habit is deactivated (soft deleted)
            if not habit.is_active:
                 TodoList.objects.filter(
                     user=user, 
                     text=old_text, 
                     is_daily=True, 
                     create_time=today,
                     done=False # Only remove if not done
                 ).delete()
            
            # If text/icon changed and is_active is still True
            elif habit.is_active:
                # Find the corresponding todo item using OLD text
                todo_qs = TodoList.objects.filter(
                    user=user,
                    text=old_text,
                    is_daily=True,
                    create_time=today
                )
                if todo_qs.exists():
                    todo_qs.update(text=habit.text, icon=habit.icon)
            
            return Response({'code': 200, 'msg': 'Habit updated'})
        return Response({'code': 400, 'msg': serializer.errors})

    def delete(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        habit_id = data.get('id')
        try:
            habit = DailyHabit.objects.get(id=habit_id, user=user)
            habit.delete()
            return Response({'code': 200, 'msg': 'Habit deleted'})
        except DailyHabit.DoesNotExist:
            return Response({'code': 404, 'msg': 'Habit not found'})
