Django 5.2.1 Stocks Party

# Running the project

python -m venv venv
source venv/bin/activate                                                                                                                    venv\Scripts\activate

pip install django djangorestframework djangorestframework-simplejwt requests python-dotenv celery redis django-environ django-filter django-celery-beat

Usually would use Celery + Redis to parse latest data that needs to be served quickly to consumers. I will skip it due to public auto-deploy hosting.
Public auto-deploy hosting also means we will use a simple sqlite database with no credentials.
Also for interview evaluation simplicity purposes I will put the database in the root of the git project.

python manage.py migrate

>>>
python manage.py migrate django_celery_beat

Run Celery worker and beat (in separate terminals):
celery -A financial_analyzer worker -l INFO
celery -A financial_analyzer beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
<<<

