import json
import traceback
from typing import List, Optional

import boto3

from ..core.exceptions.http_exceptions import InternalServerErrorException
from ..core.logging import get_logger
from ..repositories.restaurant_repository import RestaurantRepository
from ..schemas.restaurant import GoogleMapsRestaurantData, Restaurant, RestaurantCreate, RestaurantUpdate

logger = get_logger(__name__)


class RestaurantService:
    def __init__(self):
        logger.info("Initializing RestaurantService")
        try:
            self.lambda_client = boto3.client("lambda", region_name="ap-southeast-2")
            self.restaurant_repo = RestaurantRepository()
            logger.info("RestaurantService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RestaurantService: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def search_restaurants(
        self, address: str, radius: Optional[int] = 5000
    ) -> List[GoogleMapsRestaurantData]:
        """
        Search for restaurants near an address using Google Maps Places API

        Args:
            address: The address to search around
            radius: Search radius in meters (default 5000m)

        Returns:
            List of restaurant data from Google Maps
        """
        logger.info(
            f"Searching for restaurants near '{address}' within {radius}m radius"
        )

        # Prepare the payload for the Lambda function
        payload = {"address": address, "radius": radius}
        logger.debug(f"Lambda payload: {payload}")

        try:
            # Invoke the Lambda function
            logger.info("Invoking Lambda function for restaurant search")
            response = self.lambda_client.invoke(
                FunctionName="arn:aws:lambda:ap-southeast-2:700723066985:function:mealsteals-dealfinder",
                InvocationType="RequestResponse",
                Payload=json.dumps(payload),
            )

            # Parse the response from the Lambda function
            result = json.loads(response["Payload"].read().decode("utf-8"))
            logger.debug(f"Lambda response received: {len(str(result))} characters")

            # Check if the Lambda function returned an error
            if "errorMessage" in result:
                logger.error(
                    f"Lambda function returned an error: {result['errorMessage']}"
                )
                if "errorType" in result:
                    logger.error(f"Error type: {result['errorType']}")
                if "stackTrace" in result:
                    logger.error(f"Lambda stack trace: {result['stackTrace']}")
                raise InternalServerErrorException(
                    detail="An error occurred while searching for nearby restaurants."
                )

            # Convert raw Lambda response data to GoogleMapsRestaurantData objects
            restaurants = []
            logger.info(f"Processing {len(result)} restaurants from Lambda response")

            for i, restaurant_data in enumerate(result):
                try:
                    logger.debug(
                        f"Processing restaurant {i+1}: {restaurant_data.get('name', 'Unknown')}"
                    )
                    # Create GoogleMapsRestaurantData object from raw data
                    gmaps_restaurant = GoogleMapsRestaurantData(**restaurant_data)
                    restaurants.append(gmaps_restaurant)
                except Exception as e:
                    logger.warning(f"Error parsing restaurant data {i+1}: {str(e)}")
                    logger.debug(f"Failed restaurant data: {restaurant_data}")
                    continue

            logger.info(f"Successfully processed {len(restaurants)} restaurants")
            return restaurants

        except InternalServerErrorException:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Error invoking Lambda function: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException(
                detail="An error occurred while searching for nearby restaurants."
            )

    def create_restaurant(self, restaurant_data: RestaurantCreate) -> Restaurant:
        """
        Create a new restaurant

        Args:
            restaurant_data: Restaurant creation data

        Returns:
            Created restaurant
        """
        logger.info(f"Creating new restaurant: {restaurant_data.name}")
        try:
            result = self.restaurant_repo.create(restaurant_data)
            logger.info(f"Successfully created restaurant with UUID: {result.uuid}")
            return result
        except Exception as e:
            logger.error(
                f"Failed to create restaurant '{restaurant_data.name}': {str(e)}"
            )
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def get_restaurant_by_uuid(self, uuid: str) -> Optional[Restaurant]:
        """
        Get restaurant by UUID

        Args:
            uuid: Restaurant UUID

        Returns:
            Restaurant if found, None otherwise
        """
        logger.debug(f"Getting restaurant by UUID: {uuid}")
        try:
            result = self.restaurant_repo.get_by_uuid(uuid)
            if result:
                logger.debug(f"Found restaurant: {result.name}")
            else:
                logger.debug(f"Restaurant not found for UUID: {uuid}")
            return result
        except Exception as e:
            logger.error(f"Error getting restaurant by UUID {uuid}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def get_restaurant_by_gmaps_id(self, gmaps_id: str) -> Optional[Restaurant]:
        """
        Get restaurant by Google Maps ID

        Args:
            gmaps_id: Google Maps place ID

        Returns:
            Restaurant if found, None otherwise
        """
        logger.debug(f"Getting restaurant by Google Maps ID: {gmaps_id}")
        try:
            result = self.restaurant_repo.get_by_gmaps_id(gmaps_id)
            if result:
                logger.debug(f"Found existing restaurant: {result.name}")
            else:
                logger.debug(f"No existing restaurant found for gmaps_id: {gmaps_id}")
            return result
        except Exception as e:
            logger.error(f"Error getting restaurant by gmaps_id {gmaps_id}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def update_restaurant(
        self, uuid: str, restaurant_data: RestaurantCreate
    ) -> Optional[Restaurant]:
        """
        Update an existing restaurant

        Args:
            uuid: Restaurant UUID to update
            restaurant_data: Updated restaurant data

        Returns:
            Updated restaurant if successful, None if not found
        """
        logger.info(f"Updating restaurant {uuid}: {restaurant_data.name}")
        try:
            result = self.restaurant_repo.update(uuid, restaurant_data)
            if result:
                logger.info(f"Successfully updated restaurant: {result.name}")
            else:
                logger.warning(f"Restaurant not found for update: {uuid}")
            return result
        except Exception as e:
            logger.error(f"Failed to update restaurant {uuid}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def delete_restaurant(self, uuid: str) -> bool:
        """
        Delete a restaurant (soft delete)

        Args:
            uuid: Restaurant UUID to delete

        Returns:
            True if deleted successfully, False if not found
        """
        logger.info(f"Deleting restaurant: {uuid}")
        try:
            result = self.restaurant_repo.delete(uuid)
            if result:
                logger.info(f"Successfully deleted restaurant: {uuid}")
            else:
                logger.warning(f"Restaurant not found for deletion: {uuid}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete restaurant {uuid}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def list_restaurants(self, limit: int = 100) -> List[Restaurant]:
        """
        List all restaurants

        Args:
            limit: Maximum number of restaurants to return

        Returns:
            List of restaurants
        """
        logger.info(f"Listing restaurants (limit: {limit})")
        try:
            result = self.restaurant_repo.list_all(limit)
            logger.info(f"Found {len(result)} restaurants")
            return result
        except Exception as e:
            logger.error(f"Failed to list restaurants: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def list_restaurants_filtered(
        self,
        limit: int = 100,
        suburb: Optional[str] = None,
        postcode: Optional[str] = None,
        is_open_now: Optional[bool] = None,
    ) -> List[Restaurant]:
        """
        List restaurants with filters applied

        Args:
            limit: Maximum number of restaurants to return
            suburb: Filter by suburb (case-insensitive)
            postcode: Filter by postcode
            is_open_now: Filter by whether restaurant is currently open

        Returns:
            List of restaurants matching the filters
        """
        logger.info(
            f"Listing filtered restaurants - limit: {limit}, suburb: {suburb}, postcode: {postcode}, is_open_now: {is_open_now}"
        )
        try:
            # Get filtered results from repository (suburb and postcode filtering)
            restaurants = self.restaurant_repo.list_filtered(
                limit=limit
                if is_open_now is None
                else limit * 2,  # Get more if we need to filter by open status
                suburb=suburb,
                postcode=postcode,
            )

            logger.info(f"Initial restaurants before is open now : {len(restaurants)}")
            # Apply "is open now" filter if requested
            if is_open_now:
                filtered_restaurants = []
                for restaurant in restaurants:
                    if self._is_restaurant_open_now(restaurant):
                        filtered_restaurants.append(restaurant)
                        if len(filtered_restaurants) >= limit:
                            break
                restaurants = filtered_restaurants

            logger.info(f"Found {len(restaurants)} restaurants after filtering")
            return restaurants
        except Exception as e:
            logger.error(f"Failed to list filtered restaurants: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException()

    def _is_restaurant_open_now(self, restaurant: Restaurant) -> bool:
        """
        Check if a restaurant is currently open based on its open_hours
        Uses the restaurant's stored timezone

        Args:
            restaurant: Restaurant object with open_hours and timezone

        Returns:
            True if restaurant is currently open, False otherwise
        """
        if not restaurant.open_hours:
            logger.debug(
                f"No open hours available for {restaurant.name}, assuming closed"
            )
            return False

        try:
            import re

            # Get current time in the restaurant's timezone
            local_time = self._get_local_time_from_timezone(restaurant.timezone)
            if not local_time:
                logger.warning(
                    f"Could not get local time for {restaurant.name}, assuming closed"
                )
                return False

            current_day = local_time.strftime(
                "%A"
            )  # Full day name (Monday, Tuesday, etc.)
            current_time = local_time.time()

            logger.debug(
                f"Checking if {restaurant.name} is open - Local time: {current_day} {current_time} ({restaurant.timezone})"
            )

            for hours_entry in restaurant.open_hours:
                if not hours_entry:
                    continue

                # Parse different formats of opening hours
                # Examples: "Monday: 9:00 AM – 5:00 PM", "Mon-Fri: 9AM-5PM", "Open 24 hours"

                # Check for "Open 24 hours" or similar
                if "24 hours" in hours_entry.lower() or "24/7" in hours_entry.lower():
                    logger.debug(f"{restaurant.name} is open 24 hours")
                    return True

                # Check for "Closed" entries
                if "closed" in hours_entry.lower():
                    continue

                # Try to parse day and time ranges
                # Pattern for "Monday: 9:00 AM – 5:00 PM" or "Mon: 9AM-5PM"
                day_time_pattern = r"(\w+(?:-\w+)?)\s*:\s*(.+)"
                match = re.match(day_time_pattern, hours_entry)

                if not match:
                    continue

                day_part = match.group(1).strip()
                time_part = match.group(2).strip()

                # Check if current day matches
                if self._day_matches(current_day, day_part):
                    # Parse time range
                    if self._is_time_in_range(current_time, time_part):
                        logger.debug(
                            f"{restaurant.name} is open - matched {hours_entry}"
                        )
                        return True

            logger.debug(f"{restaurant.name} is closed")
            return False

        except Exception as e:
            logger.warning(f"Error checking if {restaurant.name} is open: {str(e)}")
            # If we can't parse the hours, assume closed for safety
            return False

    def _get_local_time_from_timezone(self, timezone_str: Optional[str]):
        """
        Get the current local time for a stored timezone string

        Args:
            timezone_str: Timezone string (e.g., "Australia/Sydney")

        Returns:
            datetime object in local timezone, or None if timezone lookup fails
        """
        if not timezone_str:
            return None

        try:
            from datetime import datetime

            import pytz

            # Get timezone object
            local_tz = pytz.timezone(timezone_str)

            # Get current time in UTC and convert to local timezone
            utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
            local_time = utc_now.astimezone(local_tz)

            return local_time

        except ImportError as e:
            logger.warning(f"pytz not installed: {str(e)}")
            return None
        except Exception as e:
            logger.warning(
                f"Error getting local time for timezone {timezone_str}: {str(e)}"
            )
            return None

    def _day_matches(self, current_day: str, day_pattern: str) -> bool:
        """
        Check if current day matches the day pattern from opening hours

        Args:
            current_day: Current day name (e.g., "Monday")
            day_pattern: Day pattern from hours (e.g., "Mon", "Monday", "Mon-Fri")

        Returns:
            True if current day matches the pattern
        """
        # Day abbreviations mapping
        day_abbrev = {
            "Monday": ["mon", "monday"],
            "Tuesday": ["tue", "tues", "tuesday"],
            "Wednesday": ["wed", "wednesday"],
            "Thursday": ["thu", "thurs", "thursday"],
            "Friday": ["fri", "friday"],
            "Saturday": ["sat", "saturday"],
            "Sunday": ["sun", "sunday"],
        }

        day_pattern_lower = day_pattern.lower()
        current_day_lower = current_day.lower()

        # Check for exact match or abbreviation match
        if current_day_lower in day_pattern_lower:
            return True

        for abbrev in day_abbrev.get(current_day, []):
            if abbrev in day_pattern_lower:
                return True

        # Check for day ranges like "Mon-Fri"
        if "-" in day_pattern:
            try:
                start_day, end_day = day_pattern.split("-")
                start_day = start_day.strip().lower()
                end_day = end_day.strip().lower()

                # Map to day numbers (Monday=0, Sunday=6)
                day_numbers = {
                    "mon": 0,
                    "monday": 0,
                    "tue": 1,
                    "tues": 1,
                    "tuesday": 1,
                    "wed": 2,
                    "wednesday": 2,
                    "thu": 3,
                    "thurs": 3,
                    "thursday": 3,
                    "fri": 4,
                    "friday": 4,
                    "sat": 5,
                    "saturday": 5,
                    "sun": 6,
                    "sunday": 6,
                }

                current_num = day_numbers.get(current_day_lower)
                start_num = day_numbers.get(start_day)
                end_num = day_numbers.get(end_day)

                if all(x is not None for x in [current_num, start_num, end_num]):
                    # Handle week wrapping (e.g., Fri-Mon)
                    if start_num <= end_num:
                        return start_num <= current_num <= end_num
                    else:
                        return current_num >= start_num or current_num <= end_num

            except Exception:
                pass

        return False

    def _is_time_in_range(self, current_time, time_range: str) -> bool:
        """
        Check if current time falls within the given time range

        Args:
            current_time: Current time object
            time_range: Time range string (e.g., "9:00 AM – 5:00 PM", "9AM-5PM")

        Returns:
            True if current time is within the range
        """
        import re
        from datetime import time

        try:
            # Clean up the time range string
            time_range = time_range.replace("–", "-").replace("—", "-")

            # Pattern to match time ranges like "9:00 AM - 5:00 PM" or "9AM-5PM"
            time_pattern = r"(\d{1,2}):?(\d{0,2})\s*(AM|PM|am|pm)?\s*[-–—]\s*(\d{1,2}):?(\d{0,2})\s*(AM|PM|am|pm)?"
            match = re.search(time_pattern, time_range)

            if not match:
                logger.debug(f"Could not parse time range: {time_range}")
                return False

            # Extract time components
            start_hour = int(match.group(1))
            start_min = int(match.group(2)) if match.group(2) else 0
            start_period = match.group(3).upper() if match.group(3) else None

            end_hour = int(match.group(4))
            end_min = int(match.group(5)) if match.group(5) else 0
            end_period = match.group(6).upper() if match.group(6) else None

            # Convert to 24-hour format
            if start_period == "PM" and start_hour != 12:
                start_hour += 12
            elif start_period == "AM" and start_hour == 12:
                start_hour = 0

            if end_period == "PM" and end_hour != 12:
                end_hour += 12
            elif end_period == "AM" and end_hour == 12:
                end_hour = 0

            # Create time objects
            start_time = time(start_hour, start_min)
            end_time = time(end_hour, end_min)

            # Check if current time is in range
            if start_time <= end_time:
                # Normal range (e.g., 9 AM to 5 PM)
                return start_time <= current_time <= end_time
            else:
                # Overnight range (e.g., 10 PM to 2 AM)
                return current_time >= start_time or current_time <= end_time

        except Exception as e:
            logger.debug(f"Error parsing time range '{time_range}': {str(e)}")
            return False

    def search_and_filter_restaurants(
        self,
        address: str,
        radius: Optional[int] = 5000,
        limit: int = 100,
        suburb: Optional[str] = None,
        postcode: Optional[str] = None,
        is_open_now: Optional[bool] = None,
    ) -> tuple[List[Restaurant], int, int]:
        """
        Search for restaurants near an address, upsert them to database, then return filtered results

        Args:
            address: The address to search around
            radius: Search radius in meters (default 5000m)
            limit: Maximum number of restaurants to return after filtering
            suburb: Filter by suburb (case-insensitive)
            postcode: Filter by postcode
            is_open_now: Filter by whether restaurant is currently open

        Returns:
            Tuple of (filtered_restaurants, restaurants_created, restaurants_updated)
        """
        logger.info(
            f"Search and filter - address: '{address}', radius: {radius}m, filters: suburb={suburb}, postcode={postcode}, is_open_now={is_open_now}"
        )

        try:
            # First, search for restaurants using Google Maps API
            restaurants_data = self.search_restaurants(address=address, radius=radius)
            logger.info(f"Found {len(restaurants_data)} restaurants from Google Maps")

            # Process each restaurant from Google Maps (upsert to database)
            restaurants_created = 0
            restaurants_updated = 0

            for i, gmaps_restaurant in enumerate(restaurants_data):
                try:
                    logger.debug(
                        f"Processing restaurant {i+1}/{len(restaurants_data)}: {gmaps_restaurant.name}"
                    )

                    # Upsert restaurant directly from Google Maps data
                    # This will automatically decide whether to create or update
                    restaurant, was_created = self.upsert_restaurant_from_gmaps(gmaps_restaurant)

                    if was_created:
                        restaurants_created += 1
                        logger.debug(f"Created new restaurant: {restaurant.name}")
                    else:
                        restaurants_updated += 1
                        logger.debug(f"Updated existing restaurant: {restaurant.name}")

                except Exception as e:
                    logger.error(
                        f"Failed to process restaurant {i+1} ({gmaps_restaurant.name}): {str(e)}"
                    )
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Continue processing other restaurants instead of failing completely
                    continue

            # Now get the filtered restaurants from the database
            # We'll get restaurants that match the search area and apply filters
            filtered_restaurants = self._get_restaurants_in_search_area(
                restaurants_data=restaurants_data,
                limit=limit,
                suburb=suburb,
                postcode=postcode,
                is_open_now=is_open_now,
            )

            logger.info(
                f"Search and filter completed: {restaurants_created} created, {restaurants_updated} updated, {len(filtered_restaurants)} returned after filtering"
            )
            return filtered_restaurants, restaurants_created, restaurants_updated

        except Exception as e:
            logger.error(f"Search and filter failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerErrorException(
                detail=f"Search and filter failed: {str(e)}"
            )

    def _get_restaurants_in_search_area(
        self,
        restaurants_data: List,
        limit: int = 100,
        suburb: Optional[str] = None,
        postcode: Optional[str] = None,
        is_open_now: Optional[bool] = None,
    ) -> List[Restaurant]:
        """
        Get restaurants from database that were found in the search, with filters applied

        Args:
            restaurants_data: List of restaurants from Google Maps search
            limit: Maximum number of restaurants to return
            suburb: Filter by suburb (case-insensitive)
            postcode: Filter by postcode
            is_open_now: Filter by whether restaurant is currently open

        Returns:
            List of filtered restaurants
        """
        try:
            # Extract Google Maps IDs from search results
            gmaps_ids = [restaurant.gmaps_id for restaurant in restaurants_data]

            # Get all restaurants from database that match these Google Maps IDs
            all_restaurants = []
            for gmaps_id in gmaps_ids:
                restaurant = self.restaurant_repo.get_by_gmaps_id(gmaps_id)
                if restaurant:
                    all_restaurants.append(restaurant)

            logger.debug(
                f"Found {len(all_restaurants)} restaurants in database from search results"
            )

            # Apply filters
            filtered_restaurants = []
            for restaurant in all_restaurants:
                # Apply suburb filter (case-insensitive)
                if suburb and restaurant.suburb:
                    if suburb.lower() not in restaurant.suburb.lower():
                        continue

                # Apply postcode filter (exact match)
                if postcode and restaurant.postcode:
                    if postcode != restaurant.postcode:
                        continue

                # Apply "is open now" filter
                if is_open_now is not None:
                    if self._is_restaurant_open_now(restaurant) != is_open_now:
                        continue

                # Restaurant passed all filters
                filtered_restaurants.append(restaurant)

                # Stop if we've reached the limit
                if len(filtered_restaurants) >= limit:
                    break

            return filtered_restaurants

        except Exception as e:
            logger.error(f"Error filtering restaurants in search area: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def upsert_restaurant_from_gmaps(
        self, gmaps_data: GoogleMapsRestaurantData
    ) -> tuple[Restaurant, bool]:
        """
        Create or update restaurant from Google Maps data
        Only calculates timezone for new restaurants

        Args:
            gmaps_data: Google Maps restaurant data

        Returns:
            Tuple of (Restaurant, was_created: bool)
        """
        logger.info(f"Upserting restaurant from Google Maps: {gmaps_data.name} (gmaps_id: {gmaps_data.gmaps_id})")
        
        try:
            # Check if restaurant already exists by gmaps_id
            existing_restaurant = self.restaurant_repo.get_by_gmaps_id(gmaps_data.gmaps_id)
            
            if existing_restaurant:
                # Restaurant exists - update without changing timezone
                logger.debug(f"Restaurant exists, updating: {gmaps_data.name}")
                restaurant_update = self._gmaps_to_restaurant_update(gmaps_data)
                updated_restaurant = self.restaurant_repo.update_with_restaurant_update(
                    str(existing_restaurant.uuid), restaurant_update
                )
                if updated_restaurant:
                    logger.info(f"Successfully updated restaurant: {updated_restaurant.name}")
                    return updated_restaurant, False
                else:
                    raise Exception("Update operation returned None")
            else:
                # Restaurant doesn't exist - create new with timezone calculation
                logger.debug(f"Restaurant doesn't exist, creating: {gmaps_data.name}")
                restaurant_create = self._gmaps_to_restaurant_create(gmaps_data)
                new_restaurant = self.restaurant_repo.create(restaurant_create)
                logger.info(f"Successfully created restaurant: {new_restaurant.name} (UUID: {new_restaurant.uuid})")
                return new_restaurant, True
                
        except Exception as e:
            logger.error(f"Failed to upsert restaurant '{gmaps_data.name}': {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _gmaps_to_restaurant_create(self, gmaps_data: GoogleMapsRestaurantData) -> RestaurantCreate:
        """
        Convert Google Maps data to RestaurantCreate schema (with timezone calculation)
        Only used when creating new restaurants
        """
        logger.debug(f"Converting Google Maps data to RestaurantCreate for: {gmaps_data.name}")
        try:
            # Parse address components from street_address
            address_components = self._parse_street_address(gmaps_data.street_address)
            
            # Calculate timezone from coordinates (only for new restaurants)
            timezone = self._calculate_timezone(gmaps_data.latitude, gmaps_data.longitude)

            result = RestaurantCreate(
                gmaps_id=gmaps_data.gmaps_id,
                url=gmaps_data.url,
                name=gmaps_data.name,
                venue_type=gmaps_data.venue_type,
                open_hours=gmaps_data.open_hours,
                street_address=gmaps_data.street_address,
                latitude=gmaps_data.latitude,
                longitude=gmaps_data.longitude,
                # Add parsed address components
                suburb=address_components.get("suburb"),
                state=address_components.get("state"),
                postcode=address_components.get("postcode"),
                country=address_components.get("country"),
                timezone=timezone,
            )
            logger.debug(f"Successfully converted data for creation: {result.name} (timezone: {result.timezone})")
            return result
        except Exception as e:
            logger.error(f"Failed to convert Google Maps data for creation '{gmaps_data.name}': {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _gmaps_to_restaurant_update(self, gmaps_data: GoogleMapsRestaurantData) -> RestaurantUpdate:
        """
        Convert Google Maps data to RestaurantUpdate schema (without timezone calculation)
        Only used when updating existing restaurants
        """
        logger.debug(f"Converting Google Maps data to RestaurantUpdate for: {gmaps_data.name}")
        try:
            # Parse address components from street_address
            address_components = self._parse_street_address(gmaps_data.street_address)

            result = RestaurantUpdate(
                gmaps_id=gmaps_data.gmaps_id,
                url=gmaps_data.url,
                name=gmaps_data.name,
                venue_type=gmaps_data.venue_type,
                open_hours=gmaps_data.open_hours,
                street_address=gmaps_data.street_address,
                latitude=gmaps_data.latitude,
                longitude=gmaps_data.longitude,
                # Add parsed address components
                suburb=address_components.get("suburb"),
                state=address_components.get("state"),
                postcode=address_components.get("postcode"),
                country=address_components.get("country"),
                # Note: timezone is intentionally excluded to preserve existing value
            )
            logger.debug(f"Successfully converted data for update: {result.name}")
            return result
        except Exception as e:
            logger.error(f"Failed to convert Google Maps data for update '{gmaps_data.name}': {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def to_restaurant_create(
        self, gmaps_data: GoogleMapsRestaurantData
    ) -> RestaurantCreate:
        """Convert Google Maps data to RestaurantCreate schema"""
        logger.debug(
            f"Converting Google Maps data to RestaurantCreate for: {gmaps_data.name}"
        )
        try:
            # Parse address components from street_address
            address_components = self._parse_street_address(gmaps_data.street_address)

            # Calculate timezone from coordinates
            timezone = self._calculate_timezone(
                gmaps_data.latitude, gmaps_data.longitude
            )

            result = RestaurantCreate(
                gmaps_id=gmaps_data.gmaps_id,
                url=gmaps_data.url,
                name=gmaps_data.name,
                venue_type=gmaps_data.venue_type,
                open_hours=gmaps_data.open_hours,
                street_address=gmaps_data.street_address,
                latitude=gmaps_data.latitude,
                longitude=gmaps_data.longitude,
                # Add parsed address components
                suburb=address_components.get("suburb"),
                state=address_components.get("state"),
                postcode=address_components.get("postcode"),
                country=address_components.get("country"),
                timezone=timezone,
            )
            logger.debug(f"Successfully converted data for: {result.name}")
            logger.debug(
                f"Parsed address - Suburb: {result.suburb}, State: {result.state}, Postcode: {result.postcode}, Country: {result.country}, Timezone: {result.timezone}"
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to convert Google Maps data for '{gmaps_data.name}': {str(e)}"
            )
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _calculate_timezone(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Calculate timezone for given coordinates using timezonefinder

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            Timezone string (e.g., "Australia/Sydney") or None
        """
        try:
            from timezonefinder import TimezoneFinder

            # Initialize timezone finder
            tf = TimezoneFinder()

            # Get timezone name from coordinates
            timezone_name = tf.timezone_at(lat=latitude, lng=longitude)

            if not timezone_name:
                logger.warning(
                    f"Could not determine timezone for coordinates ({latitude}, {longitude})"
                )
                return None

            logger.debug(f"Timezone for ({latitude}, {longitude}): {timezone_name}")
            return timezone_name

        except ImportError as e:
            logger.warning(f"timezonefinder not installed: {str(e)}")
            logger.warning("Install with: pip install timezonefinder")
            return None
        except Exception as e:
            logger.warning(
                f"Error calculating timezone for coordinates ({latitude}, {longitude}): {str(e)}"
            )
            return None

    def _parse_street_address(self, street_address: str) -> dict:
        """
        Parse street address to extract suburb, state, postcode, and country
        Only applies parsing logic for Australian addresses.

        Args:
            street_address: Full street address string

        Returns:
            Dictionary with parsed address components
        """
        logger.debug(f"Parsing street address: {street_address}")

        # Initialize components
        components = {"suburb": None, "state": None, "postcode": None, "country": None}

        try:
            import re

            # First, check if this is an Australian address
            if not self._is_australian_address(street_address):
                logger.debug(
                    f"Address is not Australian, skipping parsing: {street_address}"
                )
                return components

            logger.debug("Detected Australian address, applying parsing logic")

            # Australian state pattern (suburb + state + postcode)
            au_pattern = r"^(.+?)\s+([A-Z]{2,3})\s+(\d{4})$"

            # Split address by commas and clean up
            parts = [part.strip() for part in street_address.split(",")]

            if len(parts) < 2:
                logger.warning(
                    f"Address has insufficient parts for parsing: {street_address}"
                )
                return components

            if len(parts) == 2:
                # Format: "29 Stanley St Plaza, South Brisbane QLD 4101, Australia"
                # But this gets split as:
                # parts[0] = "29 Stanley St Plaza"
                # parts[1] = "South Brisbane QLD 4101, Australia"

                # The second part contains everything after the first comma
                # We need to further split this to separate country if present
                second_part = parts[1]

                # Check if there's another comma (indicating country)
                if "," in second_part:
                    # Split into location and country
                    location_parts = second_part.split(",")
                    location_part = location_parts[
                        0
                    ].strip()  # "South Brisbane QLD 4101"
                    country_part = location_parts[1].strip()  # "Australia"
                    components["country"] = country_part
                else:
                    location_part = second_part  # "South Brisbane QLD 4101"

                # Now parse the location part for suburb, state, postcode
                match = re.match(au_pattern, location_part)
                if match:
                    components["suburb"] = match.group(1).strip()
                    components["state"] = match.group(2).strip()
                    components["postcode"] = match.group(3).strip()

                    # If no country was found but we have an AU state, assume Australia
                    if not components["country"] and components["state"] in [
                        "NSW",
                        "VIC",
                        "QLD",
                        "SA",
                        "WA",
                        "TAS",
                        "NT",
                        "ACT",
                    ]:
                        components["country"] = "Australia"
                else:
                    # Fallback: put everything in suburb
                    components["suburb"] = location_part

            elif len(parts) == 3:
                # Format: "Riverside Centre, 123 Eagle St, Brisbane City QLD 4000, Australia"
                # parts[0] = "Riverside Centre, 123 Eagle St" (street address)
                # parts[1] = "Brisbane City QLD 4000" (suburb + state + postcode)
                # parts[2] = "Australia" (country)

                location_part = parts[1].strip()
                components["country"] = parts[2].strip()

                # Parse the location part for suburb, state, postcode
                match = re.match(au_pattern, location_part)
                if match:
                    components["suburb"] = match.group(1).strip()
                    components["state"] = match.group(2).strip()
                    components["postcode"] = match.group(3).strip()
                else:
                    # Fallback: put everything in suburb
                    components["suburb"] = location_part

            elif len(parts) >= 4:
                # Format: "Street, Suburb, State Postcode, Country"
                components["suburb"] = parts[1].strip()

                # Parse state and postcode from third part
                state_postcode = parts[2].strip()
                state_match = re.match(r"^([A-Z]{2,3})\s+(\d{4})$", state_postcode)

                if state_match:
                    components["state"] = state_match.group(1)
                    components["postcode"] = state_match.group(2)
                else:
                    # Try to split by space and take last part as postcode
                    parts_sp = state_postcode.split()
                    if len(parts_sp) >= 2 and parts_sp[-1].isdigit():
                        components["postcode"] = parts_sp[-1]
                        components["state"] = " ".join(parts_sp[:-1])
                    else:
                        components["state"] = state_postcode

                # Fourth part is the country
                components["country"] = parts[3].strip()

            logger.debug(f"Parsed address components: {components}")
            return components

        except Exception as e:
            logger.warning(f"Error parsing street address '{street_address}': {str(e)}")
            return components

    def _is_australian_address(self, street_address: str) -> bool:
        """
        Check if the given address is an Australian address

        Args:
            street_address: Full street address string

        Returns:
            True if the address appears to be Australian, False otherwise
        """
        import re

        # Convert to uppercase for case-insensitive matching
        address_upper = street_address.upper()

        # Check for explicit "AUSTRALIA" mention
        if "AUSTRALIA" in address_upper:
            return True

        # Check for Australian state codes (NSW, VIC, QLD, etc.)
        au_states = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"]

        # Look for state code followed by 4-digit postcode pattern
        for state in au_states:
            pattern = rf"\b{state}\s+\d{{4}}\b"
            if re.search(pattern, address_upper):
                return True

        # Check for common Australian city names (optional additional check)
        au_cities = [
            "SYDNEY",
            "MELBOURNE",
            "BRISBANE",
            "PERTH",
            "ADELAIDE",
            "CANBERRA",
            "DARWIN",
            "HOBART",
            "GOLD COAST",
            "NEWCASTLE",
            "WOLLONGONG",
            "GEELONG",
            "TOWNSVILLE",
            "CAIRNS",
        ]

        for city in au_cities:
            if city in address_upper:
                return True

        return False

    # Legacy methods for backward compatibility with existing API endpoints
    def upsert_restaurant(
        self, restaurant_data: RestaurantCreate
    ) -> tuple[Restaurant, bool]:
        """
        Create or update restaurant based on gmaps_id (legacy method for backward compatibility)

        Args:
            restaurant_data: Restaurant data to upsert

        Returns:
            Tuple of (Restaurant, was_created: bool)
        """
        logger.info(
            f"Upserting restaurant: {restaurant_data.name} (gmaps_id: {restaurant_data.gmaps_id})"
        )
        try:
            result, was_created = self.restaurant_repo.upsert(restaurant_data)
            action = "created" if was_created else "updated"
            logger.info(
                f"Successfully {action} restaurant: {result.name} (UUID: {result.uuid})"
            )
            return result, was_created
        except Exception as e:
            logger.error(
                f"Failed to upsert restaurant '{restaurant_data.name}': {str(e)}"
            )
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def to_restaurant_create(
        self, gmaps_data: GoogleMapsRestaurantData
    ) -> RestaurantCreate:
        """Convert Google Maps data to RestaurantCreate schema (legacy method for backward compatibility)"""
        logger.debug(
            f"Converting Google Maps data to RestaurantCreate for: {gmaps_data.name}"
        )
        try:
            # Parse address components from street_address
            address_components = self._parse_street_address(gmaps_data.street_address)
            
            # Calculate timezone from coordinates
            timezone = self._calculate_timezone(gmaps_data.latitude, gmaps_data.longitude)

            result = RestaurantCreate(
                gmaps_id=gmaps_data.gmaps_id,
                url=gmaps_data.url,
                name=gmaps_data.name,
                venue_type=gmaps_data.venue_type,
                open_hours=gmaps_data.open_hours,
                street_address=gmaps_data.street_address,
                latitude=gmaps_data.latitude,
                longitude=gmaps_data.longitude,
                # Add parsed address components
                suburb=address_components.get("suburb"),
                state=address_components.get("state"),
                postcode=address_components.get("postcode"),
                country=address_components.get("country"),
                timezone=timezone,
            )
            logger.debug(f"Successfully converted data for: {result.name}")
            logger.debug(
                f"Parsed address - Suburb: {result.suburb}, State: {result.state}, Postcode: {result.postcode}, Country: {result.country}, Timezone: {result.timezone}"
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to convert Google Maps data for '{gmaps_data.name}': {str(e)}"
            )
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
