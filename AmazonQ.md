# MealSteals FastAPI Project Status

## Project Overview
Converting a Flask backend to FastAPI for the MealSteals restaurant deals application. The system searches for restaurants using Google Maps API and stores them in DynamoDB.

## Current Architecture

### Tech Stack
- **Backend**: FastAPI (migrated from Flask)
- **Database**: DynamoDB with PynamoDB ORM
- **External APIs**: Google Maps Places API (via AWS Lambda)
- **Containerization**: Docker Compose
- **Logging**: Custom colored logging with file output

### Project Structure
```
dealAPI/
├── app/
│   ├── api/v1/
│   │   ├── restaurants.py    # CRUD + search endpoints
│   │   └── root.py
│   ├── core/
│   │   ├── schemas.py        # Base schemas (UUID, Timestamp, SoftDelete)
│   │   ├── logging.py        # Custom logging setup
│   │   ├── setup.py
│   │   └── exceptions/
│   │       └── http_exceptions.py  # Custom HTTP exceptions
│   ├── models/
│   │   └── restaurant.py     # DynamoDB model with PynamoDB
│   ├── repositories/
│   │   └── restaurant_repository.py  # Data access layer
│   ├── schemas/
│   │   └── restaurant.py     # Pydantic schemas
│   ├── services/
│   │   └── restaurant_service.py    # Business logic
│   └── main.py
├── compose.yml
└── Dockerfile
```

## Key Components Implemented

### 1. Pydantic Schemas (`app/schemas/restaurant.py`)
- **RestaurantBase**: Core restaurant fields from Google Maps
- **Restaurant**: Full model with UUID, timestamps, soft delete
- **RestaurantCreate**: For creation requests with address parsing
- **GoogleMapsRestaurantData**: Raw data from Lambda function
- **RestaurantSearchRequest/Response**: Search API schemas

### 2. DynamoDB Model (`app/models/restaurant.py`)
- **RestaurantModel**: PynamoDB model with all restaurant fields
- **GmapsIdIndex**: GSI for querying by Google Maps ID
- **Features**: UUID primary key, timestamps, soft delete, address components

### 3. Repository Layer (`app/repositories/restaurant_repository.py`)
- **CRUD operations**: Create, Read, Update, Delete (soft)
- **Upsert functionality**: Create or update based on gmaps_id
- **GSI queries**: Fast lookups by Google Maps ID
- **Model-to-schema conversion**: Handles UUID serialization

### 4. Service Layer (`app/services/restaurant_service.py`)
- **Google Maps integration**: Calls AWS Lambda for restaurant search
- **Address parsing**: Extracts suburb/state/postcode for Australian addresses
- **Business logic**: Handles data conversion and validation
- **Comprehensive logging**: Detailed operation tracking

### 5. API Endpoints (`app/api/v1/restaurants.py`)
- **GET /restaurants**: List all restaurants (with limit)
- **GET /restaurants/{id}**: Get specific restaurant by UUID
- **POST /restaurants**: Create new restaurant
- **PUT /restaurants/{id}**: Update existing restaurant
- **DELETE /restaurants/{id}**: Soft delete restaurant
- **POST /restaurants/search**: Search via Google Maps + upsert to DB

### 6. Custom Exception Handling (`app/core/exceptions/http_exceptions.py`)
- **BadRequestException** (400)
- **UnauthorizedException** (401)
- **ForbiddenException** (403)
- **NotFoundException** (404)
- **DuplicateValueException** (409)
- **UnprocessableEntityException** (422)
- **RateLimitException** (429)
- **InternalServerErrorException** (500)

### 7. Logging System (`app/core/logging.py`)
- **Colored console output**: Different colors per log level
- **File logging**: app.log and errors.log
- **Detailed formatting**: Shows file:line, function name, timestamps
- **Module-specific loggers**: Easy to track which component logged what

## Key Features

### Australian Address Parsing
- **Detection**: Only parses addresses containing "Australia", AU state codes, or AU cities
- **Formats supported**:
  - `"29 Stanley St Plaza, South Brisbane QLD 4101, Australia"`
  - `"Riverside Centre, 123 Eagle St, Brisbane City QLD 4000, Australia"`
- **Extraction**: Automatically populates suburb, state, postcode, country fields
- **Regex patterns**: Handles "Suburb STATE POSTCODE" format

### Database Design
- **Primary Key**: UUID (auto-generated)
- **GSI**: gmaps_id for fast Google Maps ID lookups
- **Soft Delete**: is_deleted flag + deleted_at timestamp
- **Audit Trail**: created_at, updated_at timestamps
- **Address Components**: Separate fields for suburb, state, postcode, country

### Docker Setup
- **DynamoDB Local**: Running on port 8000
- **FastAPI**: Running on port 5000 with hot reload
- **Networking**: Services communicate via Docker network
- **Volumes**: Code and logs mounted for development

## Current Issues Resolved
1. ✅ **UUID Serialization**: Fixed JSON serialization with @field_serializer
2. ✅ **DynamoDB Connection**: Fixed container networking (dealdb:8000)
3. ✅ **Address Parsing**: Robust parsing for Australian address formats
4. ✅ **Repository Pattern**: Clean separation of data access logic
5. ✅ **Comprehensive Logging**: Full request/error tracking

## Architecture Patterns Used

### Repository Pattern
- **Purpose**: Separates data access logic from business logic
- **Benefits**: Easy testing, database-agnostic code, centralized queries
- **Implementation**: RestaurantRepository handles all DynamoDB operations

### Service Layer Pattern
- **Purpose**: Contains business logic and orchestrates operations
- **Benefits**: Clean separation of concerns, reusable business logic
- **Implementation**: RestaurantService handles Google Maps integration and data conversion

### Schema Separation
- **RestaurantBase**: Core fields for input/output
- **Restaurant**: Full model with system fields (UUID, timestamps)
- **RestaurantCreate**: Input validation with extra fields allowed
- **Benefits**: Clear API contracts, validation, backward compatibility

## Next Steps / TODO
- [ ] Add cuisine extraction from Google Maps venue types
- [ ] Implement restaurant image handling
- [ ] Add search filters (by cuisine, location, etc.)
- [ ] Add pagination for restaurant listings
- [ ] Implement caching layer
- [ ] Add API rate limiting
- [ ] Add comprehensive test suite
- [ ] Add API documentation with OpenAPI/Swagger
- [ ] Implement deal management endpoints
- [ ] Add restaurant reviews/ratings

## Environment Variables
```bash
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_SESSION_TOKEN=<your-token>
AWS_DEFAULT_REGION=ap-southeast-2
ENVIRONMENT=local
RESTAURANT_TABLE_NAME=restaurants
```

## Docker Commands
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f dealapi

# Rebuild after changes
docker-compose up --build

# Create DynamoDB data directory (if needed)
mkdir -p ./docker/dynamodb
```

## API Testing Examples
```bash
# Search for restaurants
curl -X POST "http://localhost:5000/api/v1/restaurants/search" \
  -H "Content-Type: application/json" \
  -d '{"address": "Brisbane CBD", "radius": 2000}'

# Get all restaurants
curl "http://localhost:5000/api/v1/restaurants"

# Get specific restaurant
curl "http://localhost:5000/api/v1/restaurants/{uuid}"

# Create restaurant
curl -X POST "http://localhost:5000/api/v1/restaurants" \
  -H "Content-Type: application/json" \
  -d '{
    "gmaps_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
    "url": "https://example.com",
    "name": "Test Restaurant",
    "venue_type": ["Restaurant"],
    "open_hours": ["Mon-Fri: 9AM-5PM"],
    "street_address": "123 Test St, Brisbane City QLD 4000, Australia",
    "latitude": -27.4698,
    "longitude": 153.0251
  }'
```

## Key Learnings
1. **Repository Pattern**: Excellent for separating data access from business logic
2. **Pydantic Schemas**: Powerful for validation and serialization
3. **PynamoDB**: Good DynamoDB ORM but requires careful UUID handling
4. **FastAPI**: Excellent auto-documentation and validation
5. **Docker Networking**: Service names for inter-container communication
6. **Address Parsing**: Regex patterns work well for structured address formats
7. **Logging**: Comprehensive logging is crucial for debugging distributed systems
8. **Exception Handling**: Custom exceptions provide better API error responses

## Common Issues & Solutions

### UUID Serialization Error
**Problem**: `Object of type UUID is not JSON serializable`
**Solution**: Add `@field_serializer("uuid")` to convert UUID to string

### DynamoDB Connection Error
**Problem**: `Could not connect to the endpoint URL: "http://dealdb:8000/"`
**Solution**: Use Docker service name `dealdb:8000` instead of `localhost:8000`

### Address Parsing Issues
**Problem**: Incorrect parsing of Australian addresses
**Solution**: Implement Australian-specific detection and regex patterns

### Repository UUID Conversion
**Problem**: Passing UUID objects to DynamoDB queries
**Solution**: Convert UUID objects to strings with `str(uuid)` before database calls

## File Locations Summary
- **Main App**: `dealAPI/app/main.py`
- **API Routes**: `dealAPI/app/api/v1/restaurants.py`
- **Business Logic**: `dealAPI/app/services/restaurant_service.py`
- **Data Access**: `dealAPI/app/repositories/restaurant_repository.py`
- **Database Model**: `dealAPI/app/models/restaurant.py`
- **Schemas**: `dealAPI/app/schemas/restaurant.py`
- **Logging**: `dealAPI/app/core/logging.py`
- **Exceptions**: `dealAPI/app/core/exceptions/http_exceptions.py`
- **Docker**: `compose.yml`
