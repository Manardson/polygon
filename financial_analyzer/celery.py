import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financial_analyzer.settings')
app = Celery('financial_analyzer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks() # Looks for tasks.py in installed apps

# Example periodic task schedule
app.conf.beat_schedule = {
    'fetch-stock-data-every-minute': {
        'task': 'stocks_api.tasks.fetch_and_process_stock_data_task',
        'schedule': crontab(minute='*/1'),
        'args': (['GOOGL', 'AMZN', 'MSFT'],)
    },
}