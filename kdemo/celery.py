"""
import os
from celery import Celery
from celery.schedules import crontab

# 获取当前文件夹名，即为该Django的项目名
project_name = os.path.split(os.path.abspath('.'))[-1]
project_settings = '%s.settings' % project_name

# 设置环境变量
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', project_settings)

app = Celery(project_name)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

init_text = ["AD", "钙", "大便", "益生菌"]
app.conf.beat_schedule = {
    # Executes every Monday morning at 7:30 a.m.
    'add-every-morning-todo': {
        'task': 'tasks.init_todo',
        # 'schedule': crontab(minute=14, hour=19),  # 凌晨 init todolist things
        'schedule': 10.0,  # 凌晨 init todolist things
        'args': (init_text),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

"""
