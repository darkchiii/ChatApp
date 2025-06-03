import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'messaging_app.settings')

app = Celery('messaging_app')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
