import traceback
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pynamodb.exceptions import DoesNotExist, PutError, UpdateError

from ..core.logging import get_logger
from ..models.restaurant import RestaurantModel
from ..schemas.restaurant import Restaurant, RestaurantCreate, RestaurantUpdate

logger = get_logger(__name__)


class RestaurantRepository:
    """
    Repository for Restaurant data access operations
    Handles all DynamoDB interactions for restaurants
    """

    def __init__(self):
        logger.info("Initializing RestaurantRepository")
        try:
            # Ensure table exists when repository is initialized
            RestaurantModel.create_table_if_not_exists()
            logger.info("RestaurantRepository initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RestaurantRepository: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def create(self, restaurant_data: RestaurantCreate) -> Restaurant:
        """
        Create a new restaurant in the database

        Args:
            restaurant_data: RestaurantCreate schema with restaurant data

        Returns:
            Restaurant schema with created restaurant data

        Raises:
            Exception: If restaurant creation fails
        """
        try:
            # Create new restaurant model instance
            restaurant_model = RestaurantModel(
                gmaps_id=restaurant_data.gmaps_id,
                url=str(restaurant_data.url),
                name=restaurant_data.name,
                venue_type=restaurant_data.venue_type,
                open_hours=restaurant_data.open_hours,
                street_address=restaurant_data.street_address,
                latitude=float(restaurant_data.latitude),
                longitude=float(restaurant_data.longitude),
                # Add parsed address components
                cuisine=restaurant_data.cuisine,
                suburb=restaurant_data.suburb,
                state=restaurant_data.state,
                postcode=restaurant_data.postcode,
                country=restaurant_data.country,
                timezone=restaurant_data.timezone,
            )

            # Save to DynamoDB
            restaurant_model.save()

            # Convert back to Pydantic schema
            return self._model_to_schema(restaurant_model)

        except PutError as e:
            raise Exception(f"Failed to create restaurant: {str(e)}")

    def get_by_uuid(self, uuid: str) -> Optional[Restaurant]:
        """
        Get restaurant by UUID (primary key)

        Args:
            uuid: Restaurant UUID

        Returns:
            Restaurant schema if found, None otherwise
        """
        try:
            restaurant_model = RestaurantModel.get(uuid)

            # Check if soft deleted
            if restaurant_model.is_deleted:
                return None

            return self._model_to_schema(restaurant_model)

        except DoesNotExist:
            return None

    def get_by_gmaps_id(self, gmaps_id: str) -> Optional[Restaurant]:
        """
        Get restaurant by Google Maps ID using GSI

        Args:
            gmaps_id: Google Maps place ID

        Returns:
            Restaurant schema if found, None otherwise
        """
        try:
            # Query the GSI for gmaps_id
            results = list(RestaurantModel.gmaps_id_index.query(gmaps_id))

            if not results:
                return None

            # Get the first non-deleted result
            for restaurant_model in results:
                if not restaurant_model.is_deleted:
                    return self._model_to_schema(restaurant_model)

            return None

        except Exception as e:
            print(f"Error querying by gmaps_id: {str(e)}")
            return None

    def update(
        self, uuid: str, restaurant_data: RestaurantCreate
    ) -> Optional[Restaurant]:
        """
        Update an existing restaurant

        Args:
            uuid: Restaurant UUID to update
            restaurant_data: New restaurant data

        Returns:
            Updated Restaurant schema if successful, None if not found

        Raises:
            Exception: If update fails
        """
        try:
            restaurant_model = RestaurantModel.get(uuid)

            # Check if soft deleted
            if restaurant_model.is_deleted:
                return None

            # Update fields
            restaurant_model.gmaps_id = restaurant_data.gmaps_id
            restaurant_model.url = str(restaurant_data.url)
            restaurant_model.name = restaurant_data.name
            restaurant_model.venue_type = restaurant_data.venue_type
            restaurant_model.open_hours = restaurant_data.open_hours
            restaurant_model.street_address = restaurant_data.street_address
            restaurant_model.latitude = float(restaurant_data.latitude)
            restaurant_model.longitude = float(restaurant_data.longitude)
            # Update parsed address components
            restaurant_model.cuisine = restaurant_data.cuisine
            restaurant_model.suburb = restaurant_data.suburb
            restaurant_model.state = restaurant_data.state
            restaurant_model.postcode = restaurant_data.postcode
            restaurant_model.country = restaurant_data.country
            restaurant_model.timezone = restaurant_data.timezone

            # Save updates (this will automatically update updated_at)
            restaurant_model.save()

            return self._model_to_schema(restaurant_model)

        except DoesNotExist:
            return None
    def update_with_restaurant_update(self, uuid: str, restaurant_data: RestaurantUpdate) -> Optional[Restaurant]:
        """
        Update an existing restaurant using RestaurantUpdate schema (preserves timezone)
        
        Args:
            uuid: Restaurant UUID to update
            restaurant_data: New restaurant data (without timezone)
            
        Returns:
            Updated Restaurant schema if successful, None if not found
            
        Raises:
            Exception: If update fails
        """
        try:
            restaurant_model = RestaurantModel.get(uuid)
            
            # Check if soft deleted
            if restaurant_model.is_deleted:
                return None
            
            # Update fields (preserve existing timezone)
            restaurant_model.gmaps_id = restaurant_data.gmaps_id
            restaurant_model.url = str(restaurant_data.url)
            restaurant_model.name = restaurant_data.name
            restaurant_model.venue_type = restaurant_data.venue_type
            restaurant_model.open_hours = restaurant_data.open_hours
            restaurant_model.street_address = restaurant_data.street_address
            restaurant_model.latitude = float(restaurant_data.latitude)
            restaurant_model.longitude = float(restaurant_data.longitude)
            # Update parsed address components
            restaurant_model.cuisine = restaurant_data.cuisine
            restaurant_model.suburb = restaurant_data.suburb
            restaurant_model.state = restaurant_data.state
            restaurant_model.postcode = restaurant_data.postcode
            restaurant_model.country = restaurant_data.country
            # Note: timezone is intentionally NOT updated to preserve existing value
            
            # Save updates (this will automatically update updated_at)
            restaurant_model.save()
            
            return self._model_to_schema(restaurant_model)
            
        except DoesNotExist:
            return None
        except UpdateError as e:
            raise Exception(f"Failed to update restaurant: {str(e)}")

    def delete(self, uuid: str) -> bool:
        """
        Soft delete a restaurant

        Args:
            uuid: Restaurant UUID to delete

        Returns:
            True if deleted successfully, False if not found
        """
        try:
            restaurant_model = RestaurantModel.get(uuid)

            # Perform soft delete
            restaurant_model.soft_delete()
            return True

        except DoesNotExist:
            return False

    def list_all(self, limit: int = 100) -> List[Restaurant]:
        """
        List all non-deleted restaurants

        Args:
            limit: Maximum number of restaurants to return

        Returns:
            List of Restaurant schemas
        """
        try:
            restaurants = []

            # Scan the table (be careful with this in production)
            for restaurant_model in RestaurantModel.scan(limit=limit):
                if not restaurant_model.is_deleted:
                    restaurants.append(self._model_to_schema(restaurant_model))

            return restaurants

        except Exception as e:
            print(f"Error listing restaurants: {str(e)}")
            return []

    def list_filtered(
        self,
        limit: int = 100,
        suburb: Optional[str] = None,
        postcode: Optional[str] = None,
    ) -> List[Restaurant]:
        """
        List restaurants with filters applied

        Args:
            limit: Maximum number of restaurants to return
            suburb: Filter by suburb (case-insensitive)
            postcode: Filter by postcode

        Returns:
            List of Restaurant schemas matching the filters
        """
        try:
            restaurants = []
            count = 0

            # Scan the table and apply filters
            for restaurant_model in RestaurantModel.scan():
                # Skip deleted restaurants
                if restaurant_model.is_deleted:
                    continue

                # Apply suburb filter (case-insensitive)
                if suburb and (
                    not restaurant_model.suburb
                    or suburb.lower() not in restaurant_model.suburb.lower()
                ):
                    continue

                # Apply postcode filter (exact match)
                if postcode and (
                    not restaurant_model.postcode
                    or postcode != restaurant_model.postcode
                ):
                    continue

                # Add to results
                restaurants.append(self._model_to_schema(restaurant_model))
                count += 1

                # Stop if we've reached the limit
                if count >= limit:
                    break

            return restaurants

        except Exception as e:
            logger.error(f"Error listing filtered restaurants: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def upsert(self, restaurant_data: RestaurantCreate) -> tuple[Restaurant, bool]:
        """
        Create or update restaurant based on gmaps_id

        Args:
            restaurant_data: Restaurant data to upsert

        Returns:
            Tuple of (Restaurant schema, was_created: bool)
        """
        # Check if restaurant exists by gmaps_id
        existing_restaurant = self.get_by_gmaps_id(restaurant_data.gmaps_id)

        if existing_restaurant:
            # Update existing restaurant - convert UUID object to string
            updated_restaurant = self.update(
                str(existing_restaurant.uuid), restaurant_data
            )
            return updated_restaurant, False
        else:
            # Create new restaurant
            new_restaurant = self.create(restaurant_data)
            return new_restaurant, True

    def _model_to_schema(self, model: RestaurantModel) -> Restaurant:
        """
        Convert PynamoDB model to Pydantic schema

        Args:
            model: RestaurantModel instance

        Returns:
            Restaurant Pydantic schema
        """
        return Restaurant(
            uuid=model.uuid,  # Pass string directly, Pydantic will handle UUID conversion
            gmaps_id=model.gmaps_id,
            url=model.url,
            name=model.name,
            venue_type=model.venue_type,
            open_hours=model.open_hours,
            street_address=model.street_address,
            latitude=model.latitude,
            longitude=model.longitude,
            cuisine=model.cuisine,
            suburb=model.suburb,
            state=model.state,
            postcode=model.postcode,
            country=model.country,
            timezone=model.timezone,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            is_deleted=model.is_deleted,
        )
