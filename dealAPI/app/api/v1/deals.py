import uuid as uuid_pkg
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from ...core.exceptions.http_exceptions import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
)
from ...core.logging import get_logger
from ...schemas.deal import (
    BulkDealCreateRequest,
    BulkDealCreateResponse,
    DayOfWeek,
    Deal,
    DealCreate,
    DealSearchRequest,
    DealSearchResponse,
    DealUpdate,
    DealWithRestaurant,
    RestaurantsWithDealsForDayResponse,
    RestaurantWithDeals,
    RestaurantWithDealsForDay,
)
from ...services.deal_service import DealService

logger = get_logger(__name__)
router = APIRouter(prefix="/deals", tags=["deals"])
deal_service = DealService()


@router.get("/", response_model=List[Deal])
async def list_deals(
    restaurant_id: Optional[uuid_pkg.UUID] = Query(
        None, description="Filter deals by restaurant ID"
    ),
    day_of_week: Optional[DayOfWeek] = Query(
        None, description="Filter deals by day of week"
    ),
    max_price: Optional[Decimal] = Query(
        None, ge=0, description="Maximum price filter"
    ),
    dish_search: Optional[str] = Query(
        None, min_length=1, description="Search in dish names"
    ),
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Maximum number of deals to return"
    ),
):
    """
    List deals with optional filtering

    - **restaurant_id**: Filter deals by restaurant UUID
    - **day_of_week**: Filter deals by day of week (monday, tuesday, etc.)
    - **max_price**: Show only deals under this price
    - **dish_search**: Search for deals containing this text in dish name
    - **limit**: Maximum number of results to return (1-100)
    """
    try:
        logger.info(
            f"Listing deals with filters: restaurant_id={restaurant_id}, day_of_week={day_of_week}, max_price={max_price}, dish_search={dish_search}, limit={limit}"
        )

        # If any filters are provided, use filtered search
        if any([restaurant_id, day_of_week, max_price, dish_search]):
            search_request = DealSearchRequest(
                restaurant_id=restaurant_id,
                day_of_week=day_of_week,
                max_price=max_price,
                dish_search=dish_search,
            )
            search_response = deal_service.search_deals(search_request, limit=limit)
            return search_response.deals
        else:
            # No filters, return all deals
            return deal_service.list_deals(limit=limit)

    except Exception as e:
        logger.error(f"Error listing deals: {str(e)}")
        raise InternalServerErrorException(f"Failed to list deals: {str(e)}")


@router.get("/{deal_id}", response_model=Deal)
async def get_deal(deal_id: uuid_pkg.UUID):
    """
    Get a specific deal by UUID
    """
    try:
        logger.info(f"Fetching deal {deal_id}")
        return deal_service.get_deal(deal_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching deal {deal_id}: {str(e)}")
        raise InternalServerErrorException(f"Failed to fetch deal: {str(e)}")


@router.post("/", response_model=Deal, status_code=status.HTTP_201_CREATED)
async def create_deal(deal_data: DealCreate):
    """
    Create a new deal
    """
    try:
        logger.info(f"Creating new deal for restaurant {deal_data.restaurant_id}")
        return deal_service.create_deal(deal_data)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating deal: {str(e)}")
        raise InternalServerErrorException(f"Failed to create deal: {str(e)}")


@router.put("/{deal_id}", response_model=Deal)
async def update_deal(deal_id: uuid_pkg.UUID, deal_update: DealUpdate):
    """
    Update an existing deal
    """
    try:
        logger.info(f"Updating deal {deal_id}")
        return deal_service.update_deal(deal_id, deal_update)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating deal {deal_id}: {str(e)}")
        raise InternalServerErrorException(f"Failed to update deal: {str(e)}")


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(deal_id: uuid_pkg.UUID):
    """
    Soft delete a deal
    """
    try:
        logger.info(f"Deleting deal {deal_id}")
        deal_service.delete_deal(deal_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting deal {deal_id}: {str(e)}")
        raise InternalServerErrorException(f"Failed to delete deal: {str(e)}")


@router.post("/search", response_model=DealSearchResponse)
async def search_deals(
    search_request: DealSearchRequest,
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Maximum number of deals to return"
    ),
):
    """
    Search deals with multiple filters

    Request body can include:
    - **restaurant_id**: Filter by restaurant UUID
    - **day_of_week**: Filter by day of week
    - **max_price**: Maximum price filter
    - **dish_search**: Search text in dish names
    """
    try:
        logger.info(f"Searching deals with request: {search_request}")
        return deal_service.search_deals(search_request, limit=limit)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching deals: {str(e)}")
        raise InternalServerErrorException(f"Failed to search deals: {str(e)}")


@router.post(
    "/bulk", response_model=BulkDealCreateResponse, status_code=status.HTTP_201_CREATED
)
async def bulk_create_deals(bulk_request: BulkDealCreateRequest):
    """
    Create multiple deals for a restaurant (typically from web scraping)

    This endpoint is designed to be called by your Lambda function that scrapes
    restaurant websites for deal information. It will:
    - Create new deals that don't exist
    - Update existing deals if price or notes have changed
    - Skip deals that haven't changed
    """
    try:
        logger.info(f"Bulk creating deals for restaurant {bulk_request.restaurant_id}")
        return deal_service.bulk_create_deals(bulk_request)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error bulk creating deals: {str(e)}")
        raise InternalServerErrorException(f"Failed to bulk create deals: {str(e)}")


# Restaurant-specific endpoints
@router.get("/restaurant/{restaurant_id}", response_model=List[Deal])
async def get_restaurant_deals(
    restaurant_id: uuid_pkg.UUID,
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Maximum number of deals to return"
    ),
):
    """
    Get all deals for a specific restaurant
    """
    try:
        logger.info(f"Fetching deals for restaurant {restaurant_id}")
        return deal_service.get_deals_by_restaurant(restaurant_id, limit=limit)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching restaurant deals {restaurant_id}: {str(e)}")
        raise InternalServerErrorException(
            f"Failed to fetch restaurant deals: {str(e)}"
        )


@router.get("/restaurant/{restaurant_id}/status")
async def get_restaurant_deal_status(restaurant_id: uuid_pkg.UUID):
    """
    Get deal scraping status for a restaurant

    This endpoint helps the frontend know if deals are still being scraped
    or if scraping is complete for a restaurant.

    Returns:
    - status: "scraping" | "complete"
    - deals_count: number of deals found
    - message: human-readable status message
    - last_updated: when restaurant was last updated
    """
    try:
        logger.info(f"Checking deal status for restaurant {restaurant_id}")

        # Get current deals count
        deals = deal_service.get_deals_by_restaurant(restaurant_id, limit=None)
        deals_count = len(deals)

        # Get restaurant info to check creation time
        from datetime import UTC, datetime, timedelta

        from ...services.restaurant_service import RestaurantService

        restaurant_service = RestaurantService()
        restaurant = restaurant_service.get_restaurant(str(restaurant_id))

        # Check if restaurant was created recently (< 5 minutes ago)
        created_recently = (
            datetime.now(UTC).replace(tzinfo=None) - restaurant.created_at
        ) < timedelta(minutes=5)

        # Determine status based on deals count and creation time
        if deals_count == 0 and created_recently:
            status = "scraping"
            message = "Deal scraping is in progress"
        elif deals_count > 0:
            status = "complete"
            message = f"Found {deals_count} deals"
        else:
            status = "complete"
            message = "No deals found for this restaurant"

        return {
            "restaurant_id": restaurant_id,
            "status": status,
            "message": message,
            "deals_count": deals_count,
            "last_updated": restaurant.updated_at or restaurant.created_at,
        }

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error checking deal status for restaurant {restaurant_id}: {str(e)}"
        )
        raise InternalServerErrorException(f"Failed to check deal status: {str(e)}")


@router.get(
    "/restaurant/{restaurant_id}/with-restaurant", response_model=RestaurantWithDeals
)
async def get_restaurant_with_deals(restaurant_id: uuid_pkg.UUID):
    """
    Get a restaurant with all its deals
    """
    try:
        logger.info(f"Fetching restaurant {restaurant_id} with deals")
        return deal_service.get_restaurant_with_deals(restaurant_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching restaurant with deals {restaurant_id}: {str(e)}")
        raise InternalServerErrorException(
            f"Failed to fetch restaurant with deals: {str(e)}"
        )


@router.get("/day/{day_of_week}", response_model=List[Deal])
async def get_deals_by_day(
    day_of_week: DayOfWeek,
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Maximum number of deals to return"
    ),
):
    """
    Get all deals for a specific day of the week
    """
    try:
        logger.info(f"Fetching deals for {day_of_week}")
        return deal_service.get_deals_by_day(day_of_week.value, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching deals for {day_of_week}: {str(e)}")
        raise InternalServerErrorException(
            f"Failed to fetch deals for {day_of_week}: {str(e)}"
        )


@router.get(
    "/restaurants-for-day/{day_of_week}",
    response_model=RestaurantsWithDealsForDayResponse,
)
async def get_restaurants_with_deals_for_day(
    day_of_week: DayOfWeek,
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Maximum number of restaurants to return"
    ),
):
    """
    Get all restaurants that have deals for a specific day of the week

    This endpoint returns restaurants along with their deals for the specified day.
    Useful for showing "What's available on Monday?" type queries.

    Args:
        day_of_week: The day of the week to search for (monday, tuesday, etc.)
        limit: Maximum number of restaurants to return

    Returns:
        RestaurantsWithDealsForDayResponse containing:
        - message: Summary message
        - day_of_week: The requested day
        - restaurants_found: Number of restaurants with deals
        - restaurants: List of restaurants with their deals for that day
    """
    try:
        logger.info(f"Fetching restaurants with deals for {day_of_week}")
        return deal_service.get_restaurants_with_deals_for_day(
            day_of_week.value, limit=limit
        )
    except BadRequestException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error fetching restaurants with deals for {day_of_week}: {str(e)}"
        )
        raise InternalServerErrorException(
            f"Failed to fetch restaurants with deals for {day_of_week}: {str(e)}"
        )
