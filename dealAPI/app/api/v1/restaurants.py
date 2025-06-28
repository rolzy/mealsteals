import traceback
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from ...core.exceptions.http_exceptions import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
)
from ...core.logging import get_logger
from ...schemas.restaurant import (
    Restaurant,
    RestaurantCreate,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
    RestaurantSearchResultResponse,
)
from ...services.restaurant_service import RestaurantService

logger = get_logger(__name__)
router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("/", response_model=List[Restaurant])
async def get_all_restaurants(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of restaurants to return",
    ),
    suburb: Optional[str] = Query(
        default=None, description="Filter by suburb (case-insensitive)"
    ),
    postcode: Optional[str] = Query(default=None, description="Filter by postcode"),
    is_open_now: Optional[bool] = Query(
        default=None, description="Filter by whether restaurant is currently open"
    ),
):
    """Get all restaurants with optional filters"""
    logger.info(
        f"Getting restaurants - limit: {limit}, suburb: {suburb}, postcode: {postcode}, is_open_now: {is_open_now}"
    )

    try:
        restaurant_service = RestaurantService()

        # Check if any filters are applied
        if suburb or postcode or is_open_now is not None:
            restaurants = restaurant_service.list_restaurants_filtered(
                limit=limit, suburb=suburb, postcode=postcode, is_open_now=is_open_now
            )
        else:
            # No filters, use the original method
            restaurants = restaurant_service.list_restaurants(limit=limit)

        logger.info(f"Successfully retrieved {len(restaurants)} restaurants")
        return restaurants

    except Exception as e:
        logger.error(f"Failed to get restaurants: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise InternalServerErrorException(
            detail=f"Failed to retrieve restaurants: {str(e)}"
        )


@router.get("/{restaurant_id}", response_model=Restaurant)
async def get_restaurant(restaurant_id: str = Path(..., description="Restaurant UUID")):
    """Get a specific restaurant by UUID"""
    logger.info(f"Getting restaurant by ID: {restaurant_id}")

    try:
        restaurant_service = RestaurantService()
        restaurant = restaurant_service.get_restaurant_by_uuid(restaurant_id)

        if not restaurant:
            logger.warning(f"Restaurant not found: {restaurant_id}")
            raise NotFoundException(
                detail=f"Restaurant with ID {restaurant_id} not found"
            )

        logger.info(f"Successfully retrieved restaurant: {restaurant.name}")
        return restaurant

    except NotFoundException:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to get restaurant {restaurant_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise InternalServerErrorException(
            detail=f"Failed to retrieve restaurant: {str(e)}"
        )


@router.post("/", response_model=Restaurant, status_code=201)
async def create_restaurant(restaurant_data: RestaurantCreate):
    """Create a new restaurant"""
    logger.info(f"Creating new restaurant: {restaurant_data.name}")

    try:
        restaurant_service = RestaurantService()

        # Check if restaurant already exists by gmaps_id
        existing_restaurant = restaurant_service.get_restaurant_by_gmaps_id(
            restaurant_data.gmaps_id
        )
        if existing_restaurant:
            logger.warning(
                f"Restaurant with gmaps_id {restaurant_data.gmaps_id} already exists"
            )
            raise BadRequestException(
                detail=f"Restaurant with Google Maps ID {restaurant_data.gmaps_id} already exists"
            )

        restaurant = restaurant_service.create_restaurant(restaurant_data)
        logger.info(
            f"Successfully created restaurant: {restaurant.name} (UUID: {restaurant.uuid})"
        )
        return restaurant

    except BadRequestException:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to create restaurant '{restaurant_data.name}': {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise InternalServerErrorException(
            detail=f"Failed to create restaurant: {str(e)}"
        )


@router.put("/{restaurant_id}", response_model=Restaurant)
async def update_restaurant(
    restaurant_data: RestaurantCreate,
    restaurant_id: str = Path(..., description="Restaurant UUID"),
):
    """Update an existing restaurant"""
    logger.info(f"Updating restaurant {restaurant_id}: {restaurant_data.name}")

    try:
        restaurant_service = RestaurantService()

        # Check if restaurant exists
        existing_restaurant = restaurant_service.get_restaurant_by_uuid(restaurant_id)
        if not existing_restaurant:
            logger.warning(f"Restaurant not found for update: {restaurant_id}")
            raise NotFoundException(
                detail=f"Restaurant with ID {restaurant_id} not found"
            )

        # Check if gmaps_id is being changed to one that already exists
        if restaurant_data.gmaps_id != existing_restaurant.gmaps_id:
            existing_gmaps_restaurant = restaurant_service.get_restaurant_by_gmaps_id(
                restaurant_data.gmaps_id
            )
            if (
                existing_gmaps_restaurant
                and str(existing_gmaps_restaurant.uuid) != restaurant_id
            ):
                logger.warning(
                    f"Cannot update: gmaps_id {restaurant_data.gmaps_id} already exists for another restaurant"
                )
                raise BadRequestException(
                    detail=f"Google Maps ID {restaurant_data.gmaps_id} is already used by another restaurant"
                )

        updated_restaurant = restaurant_service.update_restaurant(
            restaurant_id, restaurant_data
        )
        if not updated_restaurant:
            logger.error(
                f"Update operation returned None for restaurant {restaurant_id}"
            )
            raise InternalServerErrorException(detail="Update operation failed")

        logger.info(f"Successfully updated restaurant: {updated_restaurant.name}")
        return updated_restaurant

    except (NotFoundException, BadRequestException):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to update restaurant {restaurant_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise InternalServerErrorException(
            detail=f"Failed to update restaurant: {str(e)}"
        )


@router.delete("/{restaurant_id}", status_code=204)
async def delete_restaurant(
    restaurant_id: str = Path(..., description="Restaurant UUID"),
):
    """Delete a restaurant (soft delete)"""
    logger.info(f"Deleting restaurant: {restaurant_id}")

    try:
        restaurant_service = RestaurantService()

        # Check if restaurant exists
        existing_restaurant = restaurant_service.get_restaurant_by_uuid(restaurant_id)
        if not existing_restaurant:
            logger.warning(f"Restaurant not found for deletion: {restaurant_id}")
            raise NotFoundException(
                detail=f"Restaurant with ID {restaurant_id} not found"
            )

        success = restaurant_service.delete_restaurant(restaurant_id)
        if not success:
            logger.error(
                f"Delete operation returned False for restaurant {restaurant_id}"
            )
            raise InternalServerErrorException(detail="Delete operation failed")

        logger.info(f"Successfully deleted restaurant: {existing_restaurant.name}")
        # Return 204 No Content (no response body for successful deletion)

    except NotFoundException:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to delete restaurant {restaurant_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise InternalServerErrorException(
            detail=f"Failed to delete restaurant: {str(e)}"
        )


@router.post("/search", response_model=RestaurantSearchResultResponse)
async def search_restaurants(
    search_request: RestaurantSearchRequest,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of restaurants to return",
    ),
    suburb: Optional[str] = Query(
        default=None, description="Filter by suburb (case-insensitive)"
    ),
    postcode: Optional[str] = Query(default=None, description="Filter by postcode"),
    is_open_now: Optional[bool] = Query(
        default=None, description="Filter by whether restaurant is currently open"
    ),
):
    """Search for restaurants near an address using Google Maps API and return filtered results"""
    logger.info(
        f"Restaurant search request: address='{search_request.address}', radius={search_request.radius}m, filters: suburb={suburb}, postcode={postcode}, is_open_now={is_open_now}"
    )

    try:
        # Initialize the Restaurant service for logic
        restaurant_service = RestaurantService()

        # Search for restaurants and apply filters
        filtered_restaurants, restaurants_created, restaurants_updated = (
            restaurant_service.search_and_filter_restaurants(
                address=search_request.address,
                radius=search_request.radius,
                limit=limit,
                suburb=suburb,
                postcode=postcode,
                is_open_now=is_open_now,
            )
        )

        response = RestaurantSearchResultResponse(
            message=f"Found {len(filtered_restaurants)} restaurants near {search_request.address} matching your criteria",
            restaurants_found=len(filtered_restaurants),
            restaurants_created=restaurants_created,
            restaurants_updated=restaurants_updated,
            restaurants=filtered_restaurants,
        )

        logger.info(
            f"Search completed: {restaurants_created} created, {restaurants_updated} updated, {len(filtered_restaurants)} returned"
        )
        return response

    except ValueError as e:
        logger.warning(f"Bad request for restaurant search: {str(e)}")
        raise BadRequestException(detail=str(e))
    except Exception as e:
        logger.error(f"Restaurant search failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise InternalServerErrorException(detail=f"Search failed: {str(e)}")
