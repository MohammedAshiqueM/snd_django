import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'snd_backend.settings')

app = Celery('snd_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()