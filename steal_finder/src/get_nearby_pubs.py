import logging
import os
from typing import Tuple, Union

import googlemaps
from dotenv import load_dotenv

from .dynamodb import get_restaurant
from .restaurant import Restaurant

# Load environment variables from .env file
load_dotenv()

# Get the logger for this module
logger = logging.getLogger(__name__)

# Static Variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_KEYWORDS = ["pub restaurants"]
TYPE_KEYWORDS = ["bar"]
TYPE_BLACKLIST = ["night_club"]

# Setup gmaps
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)


def get_coordinates_from_address(address: str) -> Union[Tuple[float, float], None]:
    """
    Get the coordinates (latitude, longitude) for a given address.

    Args:
    address (str): The address to geocode.

    Returns:
    Union[Tuple[float, float], None]: A tuple of (latitude, longitude) if successful, None otherwise.
    """
    try:
        result = gmaps.geocode(address)
        if result:
            location = result[0]["geometry"]["location"]
            return location["lat"], location["lng"]
        else:
            logger.error(f"Unable to geocode address: {address}")
            return None
    except Exception as e:
        logger.error(f"Error geocoding address: {str(e)}")
        return None


def find_pubs(address: str, search_radius: int = 5000) -> Union[list[Restaurant], None]:
    coordinates = get_coordinates_from_address(address)
    if coordinates:
        latitude, longitude = coordinates
        logger.debug(
            f"Coordinates for {address}: Latitude {latitude}, Longitude {longitude}"
        )
    else:
        logger.error(f"Unable to get coordinates for the address: {address}")
        return None

    pubs = []

    for search_term in SEARCH_KEYWORDS:
        results = gmaps.places(
            query=search_term, location=[latitude, longitude], radius=search_radius
        )
        next_page_exist = results.get("next-page_token") is not None
        logger.debug(f"Next page exists? {next_page_exist}")
        if next_page_exist:
            logger.error("Next_page logic not implemented yet.")
            return None

        for result in results["results"]:
            if all([keyword in result["types"] for keyword in TYPE_KEYWORDS]):
                place_details = gmaps.place(result["place_id"])["result"]
                if place_details.get("website"):
                    restaurant_data = get_restaurant(place_details.get("website"))
                    if not restaurant_data:
                        restaurant_data = Restaurant(
                            {
                                "id": result.get("place_id"),
                                "name": result.get("name"),
                                "website": place_details.get("website"),
                                "hours": place_details.get("opening_hours")[
                                    "weekday_text"
                                ],
                                "address": place_details.get("formatted_address"),
                                "coordinates": place_details.get("geometry")[
                                    "location"
                                ],
                                "rating": place_details.get("rating"),
                                "serves_beer": place_details.get("serves_beer"),
                                "serves_wine": place_details.get("serves_wine"),
                                "serves_dinner": place_details.get("serves_dinner"),
                                "types": result.get("types"),
                            }
                        )
                    pubs.append(restaurant_data)
                else:
                    logger.warning(
                        f"Website data not found for {place_details.get('name')}"
                    )

    return pubs
