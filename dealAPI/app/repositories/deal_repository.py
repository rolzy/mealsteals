import uuid as uuid_pkg
from datetime import UTC, datetime
from decimal import Decimal
from typing import List, Optional

from pynamodb.exceptions import DoesNotExist

from ..core.logging import get_logger
from ..models.deal import DealModel
from ..schemas.deal import DayOfWeek, Deal, DealCreate, DealUpdate

logger = get_logger(__name__)


class DealRepository:
    """Repository for deal data access operations"""

    def create(self, deal_data: DealCreate) -> Deal:
        """Create a new deal"""
        logger.info(f"Creating new deal for restaurant {deal_data.restaurant_id}")

        deal_uuid = str(uuid_pkg.uuid4())

        # Convert Decimal to float for DynamoDB storage (handle null prices)
        price_float = float(deal_data.price) if deal_data.price is not None else None

        deal_model = DealModel(
            uuid=deal_uuid,
            restaurant_id=str(deal_data.restaurant_id),
            dish=deal_data.dish,
            price=price_float,
            day_of_week=[
                day.value for day in deal_data.day_of_week
            ],  # Convert list of enums to list of strings
            notes=deal_data.notes,
        )

        deal_model.save()
        logger.info(f"Deal created successfully with UUID: {deal_uuid}")

        return self._model_to_schema(deal_model)

    def get_by_uuid(self, deal_uuid: uuid_pkg.UUID) -> Optional[Deal]:
        """Get a deal by UUID"""
        logger.info(f"Fetching deal with UUID: {deal_uuid}")

        try:
            deal_model = DealModel.get(str(deal_uuid))
            if deal_model.is_deleted:
                logger.info(f"Deal {deal_uuid} is soft deleted")
                return None
            return self._model_to_schema(deal_model)
        except DoesNotExist:
            logger.info(f"Deal with UUID {deal_uuid} not found")
            return None

    def get_by_restaurant_id(
        self, restaurant_id: uuid_pkg.UUID, limit: Optional[int] = None
    ) -> List[Deal]:
        """Get all deals for a specific restaurant"""
        logger.info(f"Fetching deals for restaurant {restaurant_id}")

        deals = []
        query = DealModel.restaurant_id_index.query(str(restaurant_id))

        count = 0
        for deal_model in query:
            if deal_model.is_deleted:
                continue

            deals.append(self._model_to_schema(deal_model))
            count += 1

            if limit and count >= limit:
                break

        logger.info(f"Found {len(deals)} active deals for restaurant {restaurant_id}")
        return deals

    def get_by_day_of_week(
        self, day_of_week: str, limit: Optional[int] = None
    ) -> List[Deal]:
        """Get all deals for a specific day of the week"""
        logger.info(f"Fetching deals for {day_of_week}")

        deals = []
        # Since we removed the GSI, we need to scan and filter
        # This is less efficient but necessary with ListAttribute

        count = 0
        for deal_model in DealModel.scan():
            if deal_model.is_deleted:
                continue

            # Check if the day is in the list of days for this deal
            if day_of_week in deal_model.day_of_week:
                deals.append(self._model_to_schema(deal_model))
                count += 1

                if limit and count >= limit:
                    break

        logger.info(f"Found {len(deals)} active deals for {day_of_week}")
        return deals

    def list_all(self, limit: Optional[int] = None) -> List[Deal]:
        """List all active deals"""
        logger.info("Fetching all active deals")

        deals = []
        count = 0

        for deal_model in DealModel.scan():
            if deal_model.is_deleted:
                continue

            deals.append(self._model_to_schema(deal_model))
            count += 1

            if limit and count >= limit:
                break

        logger.info(f"Found {len(deals)} active deals")
        return deals

    def update(
        self, deal_uuid: uuid_pkg.UUID, deal_update: DealUpdate
    ) -> Optional[Deal]:
        """Update an existing deal"""
        logger.info(f"Updating deal {deal_uuid}")

        try:
            deal_model = DealModel.get(str(deal_uuid))

            if deal_model.is_deleted:
                logger.warning(f"Cannot update deleted deal {deal_uuid}")
                return None

            # Update fields if provided
            update_actions = []

            if deal_update.dish is not None:
                update_actions.append(DealModel.dish.set(deal_update.dish))

            if deal_update.price is not None:
                update_actions.append(
                    DealModel.price.set(
                        float(deal_update.price)
                        if deal_update.price is not None
                        else None
                    )
                )

            if deal_update.day_of_week is not None:
                update_actions.append(
                    DealModel.day_of_week.set(
                        [day.value for day in deal_update.day_of_week]
                    )
                )

            if deal_update.notes is not None:
                update_actions.append(DealModel.notes.set(deal_update.notes))

            # Always update the updated_at timestamp
            update_actions.append(
                DealModel.updated_at.set(datetime.now(UTC).replace(tzinfo=None))
            )

            if update_actions:
                deal_model.update(actions=update_actions)
                logger.info(f"Deal {deal_uuid} updated successfully")

                # Fetch the updated model
                updated_model = DealModel.get(str(deal_uuid))
                return self._model_to_schema(updated_model)
            else:
                logger.info(f"No updates provided for deal {deal_uuid}")
                return self._model_to_schema(deal_model)

        except DoesNotExist:
            logger.warning(f"Deal {deal_uuid} not found for update")
            return None

    def soft_delete(self, deal_uuid: uuid_pkg.UUID) -> bool:
        """Soft delete a deal"""
        logger.info(f"Soft deleting deal {deal_uuid}")

        try:
            deal_model = DealModel.get(str(deal_uuid))

            if deal_model.is_deleted:
                logger.info(f"Deal {deal_uuid} is already deleted")
                return True

            deal_model.update(
                actions=[
                    DealModel.is_deleted.set(True),
                    DealModel.deleted_at.set(datetime.now(UTC).replace(tzinfo=None)),
                    DealModel.updated_at.set(datetime.now(UTC).replace(tzinfo=None)),
                ]
            )

            logger.info(f"Deal {deal_uuid} soft deleted successfully")
            return True

        except DoesNotExist:
            logger.warning(f"Deal {deal_uuid} not found for deletion")
            return False

    def search_filtered(
        self,
        restaurant_id: Optional[uuid_pkg.UUID] = None,
        day_of_week: Optional[str] = None,
        max_price: Optional[Decimal] = None,
        dish_search: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Deal]:
        """Search deals with multiple filters"""
        logger.info(
            f"Searching deals with filters: restaurant_id={restaurant_id}, day_of_week={day_of_week}, max_price={max_price}, dish_search={dish_search}"
        )

        deals = []

        # Start with the most specific query
        if restaurant_id:
            # Query by restaurant_id first (most efficient)
            query_results = self.get_by_restaurant_id(restaurant_id, limit=None)
        elif day_of_week:
            # Query by day_of_week second most efficient
            query_results = self.get_by_day_of_week(day_of_week, limit=None)
        else:
            # Scan all deals (least efficient)
            query_results = self.list_all(limit=None)

        # Apply additional filters
        count = 0
        for deal in query_results:
            # Apply day_of_week filter if not already queried
            if day_of_week and not restaurant_id:
                # Check if the day is in the deal's day_of_week list
                if not any(day.value == day_of_week for day in deal.day_of_week):
                    continue

            # Apply restaurant_id filter if not already queried
            if (
                restaurant_id
                and not day_of_week
                and str(deal.restaurant_id) != str(restaurant_id)
            ):
                continue

            # Apply max_price filter (skip deals with null prices if max_price is specified)
            if max_price and (deal.price is None or deal.price > max_price):
                continue

            # Apply dish search filter (case-insensitive partial match)
            if dish_search and dish_search.lower() not in deal.dish.lower():
                continue

            deals.append(deal)
            count += 1

            if limit and count >= limit:
                break

        logger.info(f"Found {len(deals)} deals matching filters")
        return deals

    def _model_to_schema(self, deal_model: DealModel) -> Deal:
        """Convert DealModel to Deal schema"""
        # Convert list of day strings back to DayOfWeek enums with normalization
        day_of_week_enums = self._normalize_days_from_db(deal_model.day_of_week)

        # Handle price conversion with error handling
        try:
            if deal_model.price is not None:
                price = Decimal(str(deal_model.price))
            else:
                price = None  # Allow null prices
        except (ValueError, TypeError, Exception) as e:
            logger.error(
                f"Invalid price value for deal {deal_model.uuid}: {deal_model.price} - {e}"
            )
            price = None  # Default to None for invalid prices

        return Deal(
            uuid=uuid_pkg.UUID(deal_model.uuid),
            restaurant_id=uuid_pkg.UUID(deal_model.restaurant_id),
            dish=deal_model.dish,
            price=price,
            day_of_week=day_of_week_enums,
            notes=deal_model.notes,
            created_at=deal_model.created_at,
            updated_at=deal_model.updated_at,
            is_deleted=deal_model.is_deleted,
            deleted_at=deal_model.deleted_at,
        )

    def _normalize_days_from_db(self, day_strings: List[str]) -> List[DayOfWeek]:
        """Normalize day strings from database to DayOfWeek enums"""
        if not day_strings:
            return [day for day in DayOfWeek]  # Default to all days
        
        normalized_days = []
        
        for day_str in day_strings:
            if not day_str:
                continue
                
            day_lower = day_str.lower().strip()
            
            # Handle "everyday" and similar variants
            everyday_variants = [
                "everyday", "daily", "all week", "all days", "every day", 
                "7 days", "whole week", "entire week", "all"
            ]
            
            if day_lower in everyday_variants:
                return [day for day in DayOfWeek]  # Return all days
            
            # Try to match to valid DayOfWeek values
            day_mapping = {
                "monday": DayOfWeek.MONDAY,
                "tuesday": DayOfWeek.TUESDAY,
                "wednesday": DayOfWeek.WEDNESDAY,
                "thursday": DayOfWeek.THURSDAY,
                "friday": DayOfWeek.FRIDAY,
                "saturday": DayOfWeek.SATURDAY,
                "sunday": DayOfWeek.SUNDAY,
                "mon": DayOfWeek.MONDAY,
                "tue": DayOfWeek.TUESDAY,
                "wed": DayOfWeek.WEDNESDAY,
                "thu": DayOfWeek.THURSDAY,
                "fri": DayOfWeek.FRIDAY,
                "sat": DayOfWeek.SATURDAY,
                "sun": DayOfWeek.SUNDAY,
            }
            
            if day_lower in day_mapping:
                normalized_days.append(day_mapping[day_lower])
            else:
                # If we can't parse it, log a warning but don't fail
                logger.warning(f"Unknown day string from database: '{day_str}', skipping")
        
        # If we got some valid days, return them; otherwise default to all days
        return normalized_days if normalized_days else [day for day in DayOfWeek]
