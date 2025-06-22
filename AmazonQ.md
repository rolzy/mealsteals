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
- **Timezone Handling**: timezonefinder + pytz for accurate local time calculations

### Project Structure
```
dealAPI/
├── app/
│   ├── api/v1/
│   │   ├── restaurants.py    # CRUD + search endpoints with filtering
│   │   └── root.py
│   ├── core/
│   │   ├── schemas.py        # Base schemas (UUID, Timestamp, SoftDelete)
│   │   ├── logging.py        # Custom logging setup
│   │   ├── setup.py
│   │   └── exceptions/
│   │       └── http_exceptions.py  # Custom HTTP exceptions
│   ├── models/
│   │   └── restaurant.py     # DynamoDB model with PynamoDB + timezone field
│   ├── repositories/
│   │   └── restaurant_repository.py  # Data access layer with filtering
│   ├── schemas/
│   │   └── restaurant.py     # Pydantic schemas (Create/Update/Response)
│   ├── services/
│   │   └── restaurant_service.py    # Business logic with optimized upsert
│   └── main.py
├── compose.yml
└── Dockerfile
```

## Key Components Implemented

### 1. Pydantic Schemas (`app/schemas/restaurant.py`)
- **RestaurantBase**: Core restaurant fields from Google Maps
- **Restaurant**: Full model with UUID, timestamps, soft delete, timezone
- **RestaurantCreate**: For creation requests with address parsing + timezone calculation
- **RestaurantUpdate**: For updates without timezone recalculation (NEW)
- **GoogleMapsRestaurantData**: Raw data from Lambda function
- **RestaurantSearchRequest/Response**: Search API schemas
- **RestaurantSearchResultResponse**: Returns actual filtered restaurant list (NEW)

### 2. DynamoDB Model (`app/models/restaurant.py`)
- **RestaurantModel**: PynamoDB model with all restaurant fields + timezone
- **GmapsIdIndex**: GSI for querying by Google Maps ID
- **Features**: UUID primary key, timestamps, soft delete, address components, timezone storage

### 3. Repository Layer (`app/repositories/restaurant_repository.py`)
- **CRUD operations**: Create, Read, Update, Delete (soft)
- **Upsert functionality**: Create or update based on gmaps_id
- **GSI queries**: Fast lookups by Google Maps ID
- **Filtering methods**: `list_filtered()` for suburb/postcode filtering (NEW)
- **Optimized updates**: `update_with_restaurant_update()` preserves timezone (NEW)
- **Model-to-schema conversion**: Handles UUID serialization

### 4. Service Layer (`app/services/restaurant_service.py`)
- **Google Maps integration**: Calls AWS Lambda for restaurant search
- **Address parsing**: Extracts suburb/state/postcode for Australian addresses
- **Timezone calculation**: Uses timezonefinder for accurate timezone detection
- **Optimized upsert logic**: `upsert_restaurant_from_gmaps()` (NEW)
  - Only calculates timezone for new restaurants
  - Uses RestaurantUpdate for existing restaurants
  - Preserves existing timezone data
- **Opening hours logic**: Timezone-aware "is open now" calculations (NEW)
- **Filtering service**: `list_restaurants_filtered()` with multiple filter support (NEW)
- **Search with filtering**: `search_and_filter_restaurants()` (NEW)
- **Business logic**: Handles data conversion and validation
- **Comprehensive logging**: Detailed operation tracking

### 5. API Endpoints (`app/api/v1/restaurants.py`)
- **GET /restaurants**: List all restaurants with filtering support (ENHANCED)
  - Query parameters: `suburb`, `postcode`, `is_open_now`, `limit`
- **GET /restaurants/{id}**: Get specific restaurant by UUID
- **POST /restaurants**: Create new restaurant
- **PUT /restaurants/{id}**: Update existing restaurant
- **DELETE /restaurants/{id}**: Soft delete restaurant
- **POST /restaurants/search**: Search + filter restaurants (ENHANCED)
  - Returns actual filtered restaurant list instead of just summary
  - Supports same query parameters as GET /restaurants
  - Combines Google Maps search with database filtering

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

### Restaurant Filtering (NEW)
- **Suburb Filter**: Case-insensitive partial matching
- **Postcode Filter**: Exact matching
- **Is Open Now Filter**: Timezone-aware opening hours calculation
- **Combined Filters**: All filters can be used together
- **Performance Optimized**: Database-level filtering where possible

### Timezone-Aware Opening Hours (NEW)
- **Accurate Local Time**: Uses restaurant's stored timezone
- **Smart Parsing**: Handles various opening hours formats
  - "Monday: 9:00 AM – 5:00 PM"
  - "Mon-Fri: 9AM-5PM"
  - "Open 24 hours"
  - Day ranges (Mon-Fri) and overnight hours (10 PM - 2 AM)
- **Performance**: Timezone calculated once at creation, not on every query

### Optimized Search & Upsert (NEW)
- **Smart Upsert Logic**:
  1. Check if restaurant exists by gmaps_id
  2. If new → Create with timezone calculation
  3. If exists → Update without timezone recalculation
- **Performance Benefits**:
  - Timezone lookup only for genuinely new restaurants
  - Preserves existing timezone data during updates
  - Faster search results for areas with many existing restaurants

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
- **Timezone Storage**: Timezone string (e.g., "Australia/Sydney") (NEW)

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
6. ✅ **Restaurant Filtering**: Efficient filtering by suburb, postcode, open status (NEW)
7. ✅ **Timezone Optimization**: Calculate once, use many times (NEW)
8. ✅ **Search Performance**: Optimized upsert logic for better performance (NEW)

## Architecture Patterns Used

### Repository Pattern
- **Purpose**: Separates data access logic from business logic
- **Benefits**: Easy testing, database-agnostic code, centralized queries
- **Implementation**: RestaurantRepository handles all DynamoDB operations
- **Enhanced**: Added filtering methods and optimized update operations (NEW)

### Service Layer Pattern
- **Purpose**: Contains business logic and orchestrates operations
- **Benefits**: Clean separation of concerns, reusable business logic
- **Implementation**: RestaurantService handles Google Maps integration and data conversion
- **Enhanced**: Smart upsert logic and timezone-aware filtering (NEW)

### Schema Separation
- **RestaurantBase**: Core fields for input/output
- **Restaurant**: Full model with system fields (UUID, timestamps, timezone)
- **RestaurantCreate**: Input validation with timezone calculation (NEW)
- **RestaurantUpdate**: Input validation without timezone modification (NEW)
- **Benefits**: Clear API contracts, validation, backward compatibility, performance optimization

## Recent Enhancements (Tonight's Work)

### 1. Restaurant Filtering System
- **API Enhancement**: Added query parameters to GET /restaurants
- **Database Filtering**: Efficient suburb/postcode filtering at repository level
- **Service Filtering**: "Is open now" logic using stored timezone data
- **Combined Filtering**: All filters work together seamlessly

### 2. Timezone-Aware Opening Hours
- **Accurate Calculations**: Uses restaurant's local timezone for "open now" determination
- **Performance Optimized**: Timezone stored in database, not calculated on every query
- **Smart Parsing**: Handles various opening hours formats and edge cases

### 3. Enhanced Search Endpoint
- **Returns Restaurant List**: Instead of just summary statistics
- **Supports Filtering**: Same query parameters as GET /restaurants
- **Optimized Performance**: Smart upsert logic reduces unnecessary timezone calculations
- **Better UX**: Frontend can directly use filtered restaurant data

### 4. Optimized Upsert Logic
- **Smart Decision Making**: Automatically chooses create vs update based on existence
- **Performance**: Only calculates timezone for genuinely new restaurants
- **Data Integrity**: Preserves existing timezone data during updates
- **Backward Compatibility**: Legacy methods maintained for existing endpoints

## Next Steps / TODO
- [ ] Add cuisine extraction from Google Maps venue types
- [ ] Implement restaurant image handling
- [ ] Add pagination for restaurant listings
- [ ] Implement caching layer for frequently accessed data
- [ ] Add API rate limiting
- [ ] Add comprehensive test suite
- [ ] Add API documentation with OpenAPI/Swagger
- [ ] Implement deal management endpoints
- [ ] Add restaurant reviews/ratings
- [ ] Consider adding more sophisticated timezone handling for edge cases
- [ ] Add performance monitoring and metrics

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

### Basic Restaurant Operations
```bash
# Get all restaurants
curl "http://localhost:5000/api/v1/restaurants"

# Get restaurants with filters
curl "http://localhost:5000/api/v1/restaurants?suburb=Brisbane&limit=10"
curl "http://localhost:5000/api/v1/restaurants?postcode=4000&is_open_now=true"
curl "http://localhost:5000/api/v1/restaurants?suburb=Brisbane&is_open_now=true&limit=5"

# Get specific restaurant
curl "http://localhost:5000/api/v1/restaurants/{uuid}"
```

### Enhanced Search Operations
```bash
# Basic search (returns filtered restaurant list)
curl -X POST "http://localhost:5000/api/v1/restaurants/search" \
  -H "Content-Type: application/json" \
  -d '{"address": "Brisbane CBD", "radius": 2000}'

# Search with filters
curl -X POST "http://localhost:5000/api/v1/restaurants/search?suburb=Brisbane&limit=10" \
  -H "Content-Type: application/json" \
  -d '{"address": "South Brisbane", "radius": 1500}'

# Search for open restaurants only
curl -X POST "http://localhost:5000/api/v1/restaurants/search?is_open_now=true&limit=5" \
  -H "Content-Type: application/json" \
  -d '{"address": "Brisbane CBD", "radius": 2000}'

# Combined search filters
curl -X POST "http://localhost:5000/api/v1/restaurants/search?suburb=Brisbane&postcode=4000&is_open_now=true" \
  -H "Content-Type: application/json" \
  -d '{"address": "Brisbane City", "radius": 1000}'
```

### Restaurant Creation
```bash
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
9. **Timezone Handling**: Store timezone data to avoid repeated expensive calculations (NEW)
10. **Performance Optimization**: Smart upsert logic significantly improves search performance (NEW)
11. **Filtering Architecture**: Database-level filtering where possible, service-level for complex logic (NEW)

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

### Performance Issues with Filtering
**Problem**: Slow response times when filtering restaurants
**Solution**: Implement database-level filtering and optimize timezone calculations (NEW)

### Timezone Calculation Overhead
**Problem**: Expensive timezone lookup on every "is open now" check
**Solution**: Store timezone in database, calculate only once during creation (NEW)

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
- **Dependencies**: `pyproject.toml`

## Dependencies
```toml
[project]
dependencies = [
    "boto3>=1.38.36",
    "fastapi>=0.115.12",
    "pynamodb>=6.1.0",
    "uvicorn>=0.34.3",
    "timezonefinder>=6.5.2",  # For accurate timezone detection
    "pytz>=2024.1",           # For timezone handling
]
```
