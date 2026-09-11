import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megano.settings')

app = Celery('megano')
# namespace='CELERY' — значит все относящиеся к Celery настройки в
# settings.py должны начинаться с префикса CELERY_ (CELERY_BROKER_URL и т.п.)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
