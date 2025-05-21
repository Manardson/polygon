# Django Polygon Stock Analysis API - Project Documentation

## Overview
This project is a Python/Django-based web application that processes real-time financial data from Polygon.io. The application connects to Polygon's API to retrieve stock price data for Google, Amazon, and Microsoft, analyzes the data for significant price changes, and provides insights through a RESTful API.

## Features
- Real-time stock data retrieval from Polygon.io
- Asynchronous data processing using Celery
- Detection and storage of significant price change events
- RESTful API with filtering, pagination, and ordering
- JWT authentication for secure API access
- Interactive HTML test page for querying the API
- Comprehensive unit tests
- Production-ready security configurations

## API Endpoints

### Authentication
- `POST /api/token/`: Obtain JWT access and refresh tokens
- `POST /api/token/refresh/`: Refresh an access token
- `POST /api/token/verify/`: Verify an access token

### Stock Data
- `GET /api/stocks/significant-events/`: List significant price change events
- `GET /api/stocks/symbols/`: List available stock symbols
- `GET /api/stocks/price-history/`: Get price history for a specific symbol
- `GET /api/stocks/event-summary/`: Get summary statistics of significant events

### Filtering Options
- `symbol__ticker`: Filter by stock symbol (e.g., `?symbol__ticker=GOOGL`)
- `event_type`: Filter by event type (e.g., `?event_type=PRICE_INCREASE`)
- `timestamp__gte`, `timestamp__lte`: Filter by date range
- `ordering`: Sort results (e.g., `?ordering=-timestamp`)
- `page`: Paginate results (e.g., `?page=2`)

## Setup and Installation

### Prerequisites
- Python 3.8+
- Django 5.2.1+
- Polygon.io API key

### Installation Steps
1. Clone the repository
   ```
   git clone https://github.com/Manardson/polygon.git
   cd polygon
   ```

2. Create and activate a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install django djangorestframework djangorestframework-simplejwt requests python-dotenv celery redis django-environ django-filter django-celery-beat factory-boy
   pip install -r requirements.txt
   ```

4. Configure environment variables
   Create a `.env` file in the project root with the following:
   ```
   DEBUG=True
   SECRET_KEY=your_secret_key
   POLYGON_API_KEY=your_polygon_api_key
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

5. Run migrations
   ```
   python manage.py migrate
   ```

6. Create a superuser
   ```
   python manage.py createsuperuser
   ```

7. Start the development server
   ```
   python manage.py runserver
   ```

8. (Optional) Start Celery worker and beat for background tasks
   ```
   celery -A financial_analyzer worker -l INFO
   celery -A financial_analyzer beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
   ```

## Testing
Run the test suite with:
```
python manage.py test
```

## Deployment
For production deployment:
```
gunicorn financial_analyzer.wsgi:application --bind 0.0.0.0:$PORT
```

## API Usage
A Postman collection is included in the repository for easy testing of the API endpoints. Import `postman_collection.json` into Postman to get started.

## HTML Test Page
A simple HTML page is available for interactively querying the API:
```
http://localhost:8000/api/stocks/test-query-page/
```

## Architecture
The project follows a clean architecture with separation of concerns:
- Models: Define data structure
- Views: Handle HTTP requests/responses
- Serializers: Handle data validation and representation
- Services: Encapsulate business logic
- Tasks: Handle background operations

## Security
The application implements several security best practices:
- JWT authentication for API access
- HTTPS enforcement in production
- Secure cookie settings
- HSTS headers
- XSS protection
- Content type sniffing protection

## Future Enhancements
- WebSocket support for real-time updates
- Additional technical analysis indicators
- User-configurable alert thresholds
- Mobile app integration
