import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'messaging_app.settings')

app = Celery('messaging_app')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'notify-unread-daily': {
        'task': 'chat.tasks.notify_user_unread_messages',
        'schedule': crontab(hour=9, minute=0),
    },
}