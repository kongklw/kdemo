# Create your tasks here
#
# from demoapp.models import Widget
from .models import TodoList
from users.models import User

from celery import shared_task


@shared_task
def init_todo(init_text):
    # 为所有user 初始化todo things
    print('哈哈哈')
    users = User.objects.all()
    for user in users:
        for text in init_text:
            objs = TodoList(user=user, text=text)
            objs.save()
    print("已经结束")
