import uuid as uuid_pkg
from decimal import Decimal
from typing import List, Optional

import boto3

from ..core.exceptions.http_exceptions import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
)
from ..core.logging import get_logger
from ..repositories.deal_repository import DealRepository
from ..repositories.restaurant_repository import RestaurantRepository
from ..schemas.deal import (
    BulkDealCreateRequest,
    BulkDealCreateResponse,
    Deal,
    DealCreate,
    DealSearchRequest,
    DealSearchResponse,
    DealUpdate,
    DealWithRestaurant,
    RestaurantsWithDealsForDayResponse,
    RestaurantWithDeals,
    RestaurantWithDealsForDay,
    WebScrapedDealData,
)

logger = get_logger(__name__)


class DealService:
    """Service layer for deal business logic"""

    def __init__(self):
        logger.info("Initializing DealService")

        try:
            self.lambda_client = boto3.client("lambda", region_name="ap-southeast-2")
            self.deal_repository = DealRepository()
            self.restaurant_repository = RestaurantRepository()
            logger.info("DealService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DealService: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def create_deal(self, deal_data: DealCreate) -> Deal:
        """Create a new deal"""
        logger.info(f"Creating deal for restaurant {deal_data.restaurant_id}")

        # Verify restaurant exists
        restaurant = self.restaurant_repository.get_by_uuid(str(deal_data.restaurant_id))
        if not restaurant:
            raise NotFoundException(
                f"Restaurant with ID {deal_data.restaurant_id} not found"
            )

        return self.deal_repository.create(deal_data)

    def get_deal(self, deal_uuid: uuid_pkg.UUID) -> Deal:
        """Get a deal by UUID"""
        logger.info(f"Fetching deal {deal_uuid}")

        deal = self.deal_repository.get_by_uuid(deal_uuid)
        if not deal:
            raise NotFoundException(f"Deal with ID {deal_uuid} not found")

        return deal

    def get_restaurant_with_deals(
        self, restaurant_uuid: uuid_pkg.UUID
    ) -> RestaurantWithDeals:
        """Get a restaurant with all its deals"""
        logger.info(f"Fetching restaurant {restaurant_uuid} with deals")

        restaurant = self.restaurant_repository.get_by_uuid(str(restaurant_uuid))
        if not restaurant:
            raise NotFoundException(f"Restaurant with ID {restaurant_uuid} not found")

        deals = self.deal_repository.get_by_restaurant_id(restaurant_uuid)

        return RestaurantWithDeals(restaurant=restaurant, deals=deals)

    def update_deal(self, deal_uuid: uuid_pkg.UUID, deal_update: DealUpdate) -> Deal:
        """Update an existing deal"""
        logger.info(f"Updating deal {deal_uuid}")

        updated_deal = self.deal_repository.update(deal_uuid, deal_update)
        if not updated_deal:
            raise NotFoundException(f"Deal with ID {deal_uuid} not found")

        return updated_deal

    def delete_deal(self, deal_uuid: uuid_pkg.UUID) -> bool:
        """Soft delete a deal"""
        logger.info(f"Deleting deal {deal_uuid}")

        success = self.deal_repository.soft_delete(deal_uuid)
        if not success:
            raise NotFoundException(f"Deal with ID {deal_uuid} not found")

        return success

    def list_deals(self, limit: Optional[int] = None) -> List[Deal]:
        """List all active deals"""
        logger.info("Listing all deals")
        return self.deal_repository.list_all(limit=limit)

    def get_deals_by_restaurant(
        self, restaurant_uuid: uuid_pkg.UUID, limit: Optional[int] = None
    ) -> List[Deal]:
        """Get all deals for a specific restaurant"""
        logger.info(f"Fetching deals for restaurant {restaurant_uuid}")

        # Verify restaurant exists
        restaurant = self.restaurant_repository.get_by_uuid(str(restaurant_uuid))
        if not restaurant:
            raise NotFoundException(f"Restaurant with ID {restaurant_uuid} not found")

        logger.info(f"Found restaurant {restaurant.name} with ID {restaurant_uuid}")

        return self.deal_repository.get_by_restaurant_id(restaurant_uuid, limit=limit)

    def get_deals_by_day(
        self, day_of_week: str, limit: Optional[int] = None
    ) -> List[Deal]:
        """Get all deals for a specific day of the week"""
        logger.info(f"Fetching deals for {day_of_week}")
        return self.deal_repository.get_by_day_of_week(day_of_week, limit=limit)

    def search_deals(
        self, search_request: DealSearchRequest, limit: Optional[int] = None
    ) -> DealSearchResponse:
        """Search deals with filters"""
        logger.info(f"Searching deals with request: {search_request}")

        # Validate restaurant_id if provided
        if search_request.restaurant_id:
            restaurant = self.restaurant_repository.get_by_uuid(
                str(search_request.restaurant_id)
            )
            if not restaurant:
                raise NotFoundException(
                    f"Restaurant with ID {search_request.restaurant_id} not found"
                )

        deals = self.deal_repository.search_filtered(
            restaurant_id=search_request.restaurant_id,
            day_of_week=search_request.day_of_week.value
            if search_request.day_of_week
            else None,
            max_price=search_request.max_price,
            dish_search=search_request.dish_search,
            limit=limit,
        )

        return DealSearchResponse(
            message=f"Found {len(deals)} deals matching search criteria",
            deals_found=len(deals),
            deals=deals,
        )

    def bulk_create_deals(
        self, bulk_request: BulkDealCreateRequest
    ) -> BulkDealCreateResponse:
        """Create multiple deals for a restaurant (typically from web scraping)"""
        logger.info(
            f"Bulk creating {len(bulk_request.deals)} deals for restaurant {bulk_request.restaurant_id}"
        )

        # Verify restaurant exists
        restaurant = self.restaurant_repository.get_by_uuid(str(bulk_request.restaurant_id))
        if not restaurant:
            raise NotFoundException(
                f"Restaurant with ID {bulk_request.restaurant_id} not found"
            )

        # Get existing deals for this restaurant to check for duplicates
        existing_deals = self.deal_repository.get_by_restaurant_id(
            bulk_request.restaurant_id
        )
        existing_deals_map = {
            (deal.dish.lower().strip(), deal.day_of_week.value): deal
            for deal in existing_deals
        }

        created_deals = []
        updated_deals = []

        for scraped_deal in bulk_request.deals:
            deal_key = (
                scraped_deal.dish.lower().strip(),
                scraped_deal.day_of_week.value,
            )

            if deal_key in existing_deals_map:
                # Update existing deal
                existing_deal = existing_deals_map[deal_key]

                # Check if update is needed (price or notes changed)
                needs_update = (
                    existing_deal.price != scraped_deal.price
                    or existing_deal.notes != scraped_deal.notes
                )

                if needs_update:
                    deal_update = DealUpdate(
                        price=scraped_deal.price, notes=scraped_deal.notes
                    )
                    updated_deal = self.deal_repository.update(
                        existing_deal.uuid, deal_update
                    )
                    if updated_deal:
                        updated_deals.append(updated_deal)
                        logger.info(
                            f"Updated existing deal: {existing_deal.dish} for {existing_deal.day_of_week}"
                        )
                else:
                    logger.info(
                        f"No changes needed for deal: {existing_deal.dish} for {existing_deal.day_of_week}"
                    )
            else:
                # Create new deal
                deal_create = DealCreate(
                    restaurant_id=bulk_request.restaurant_id,
                    dish=scraped_deal.dish,
                    price=scraped_deal.price,
                    day_of_week=scraped_deal.day_of_week,
                    notes=scraped_deal.notes,
                )

                new_deal = self.deal_repository.create(deal_create)
                created_deals.append(new_deal)
                logger.info(
                    f"Created new deal: {scraped_deal.dish} for {scraped_deal.day_of_week}"
                )

        all_deals = created_deals + updated_deals

        logger.info(
            f"Bulk operation completed: {len(created_deals)} created, {len(updated_deals)} updated"
        )

        return BulkDealCreateResponse(
            message=f"Successfully processed {len(bulk_request.deals)} deals: {len(created_deals)} created, {len(updated_deals)} updated",
            restaurant_id=bulk_request.restaurant_id,
            deals_created=len(created_deals),
            deals_updated=len(updated_deals),
            deals=all_deals,
        )

    def get_restaurants_with_deals_for_day(
        self, day_of_week: str, limit: Optional[int] = None
    ) -> RestaurantsWithDealsForDayResponse:
        """Get all restaurants that have deals for a specific day of the week"""
        from ..schemas.deal import DayOfWeek

        logger.info(f"Fetching restaurants with deals for {day_of_week}")

        # Convert string to DayOfWeek enum for validation
        try:
            day_enum = DayOfWeek(day_of_week.lower())
        except ValueError:
            raise BadRequestException(f"Invalid day of week: {day_of_week}")

        # Get all deals for the specified day
        deals_for_day = self.deal_repository.get_by_day_of_week(day_of_week, limit=None)

        if not deals_for_day:
            return RestaurantsWithDealsForDayResponse(
                message=f"No deals found for {day_enum.value}",
                day_of_week=day_enum,
                restaurants_found=0,
                restaurants=[],
            )

        # Group deals by restaurant_id
        restaurant_deals_map = {}
        for deal in deals_for_day:
            restaurant_id = deal.restaurant_id
            if restaurant_id not in restaurant_deals_map:
                restaurant_deals_map[restaurant_id] = []
            restaurant_deals_map[restaurant_id].append(deal)

        # Get restaurant information for each restaurant with deals
        restaurants_with_deals = []
        count = 0

        for restaurant_id, deals in restaurant_deals_map.items():
            if limit and count >= limit:
                break

            # Get restaurant details
            restaurant = self.restaurant_repository.get_by_uuid(str(restaurant_id))
            if not restaurant:
                logger.warning(f"Restaurant {restaurant_id} not found, skipping deals")
                continue

            # Create RestaurantWithDealsForDay object
            restaurant_with_deals = RestaurantWithDealsForDay(
                restaurant=restaurant, deals=deals, day_of_week=day_enum
            )

            restaurants_with_deals.append(restaurant_with_deals)
            count += 1

        logger.info(
            f"Found {len(restaurants_with_deals)} restaurants with deals for {day_of_week}"
        )

        return RestaurantsWithDealsForDayResponse(
            message=f"Found {len(restaurants_with_deals)} restaurants with deals for {day_enum.value}",
            day_of_week=day_enum,
            restaurants_found=len(restaurants_with_deals),
            restaurants=restaurants_with_deals,
        )
