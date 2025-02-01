# import os
# import sys

# if __name__ == '__main__':
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'snd_backend.settings')
    
#     from celery import Celery
#     from django.conf import settings

#     app = Celery('snd_backend')
#     app.config_from_object('django.conf:settings', namespace='CELERY')
#     app.conf.broker_url = 'redis://localhost:6379/0'
#     app.conf.result_backend = 'redis://localhost:6379/0'
    
#     app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

#     app.start(argv=['worker', '--loglevel=debug', '--pool=solo'])