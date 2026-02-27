import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moodnotes_pro.settings')

app = Celery('moodnotes_pro')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
