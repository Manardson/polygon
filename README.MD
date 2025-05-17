Django 5.2.1 Stocks Party

# Superuser

test
test@test.com
mysuper

# Running the project

python -m venv venv
source venv/bin/activate                                                                                                                    venv\Scripts\activate

pip install django djangorestframework djangorestframework-simplejwt requests python-dotenv celery redis django-environ django-filter django-celery-beat factory-boy

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

# Local server

For ease of access in the interview test I put the .env and Postman Collection in git. Definitely not something to do in other scenarios.

python manage.py runserver

celery -A financial_analyzer worker -l INFO
celery -A financial_analyzer beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

# API Endpoints

A Postman collection (postman_collection.json) is provided for easy testing of the API.
The base URL for API endpoints is typically http://localhost:8000/api/.

Authentication

    POST /api/token/: Obtain JWT access and refresh tokens.

    POST /api/token/refresh/: Refresh an access token using a refresh token.

    POST /api/token/verify/: Verify an access token.

All other API endpoints require a Bearer <access_token> in the Authorization header.
Stocks API

    GET /api/stocks/significant-events/: Retrieve a list of significant stock price change events.

        Authentication: Required (JWT Bearer Token).

        Pagination: Supported (e.g., ?page=2). Page size is configured in settings.

        Filtering:

            symbol__ticker=<TICKER> (e.g., ?symbol__ticker=GOOGL)

            event_type=<EVENT_TYPE> (e.g., ?event_type=PRICE_INCREASE or PRICE_DECREASE)

            timestamp__gte=<ISO_DATETIME> (e.g., ?timestamp__gte=2023-10-26T10:00:00Z)

            timestamp__lte=<ISO_DATETIME>

            timestamp__date__gte=<YYYY-MM-DD> (e.g., ?timestamp__date__gte=2023-10-26)

        Ordering:

            ordering=<field_name> (e.g., ?ordering=timestamp or ?ordering=-timestamp for descending). Supported fields: timestamp, symbol__ticker, event_type. Default is -timestamp.

# HTML Test Page

A simple HTML page is available for interactively querying the /api/stocks/significant-events/ endpoint.

    URL: http://localhost:8000/test-query-page/


# Unit Tests

python manage.py test stocks_api

    *All Tests*

    python manage.py test


# Production deploy

gunicorn financial_analyzer.wsgi:application --bind 0.0.0.0:PORT