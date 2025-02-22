import logging
import os
from typing import Tuple, Union

import googlemaps

# Static Variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_KEYWORDS = ["pub restaurants"]
TYPE_KEYWORDS = ["bar"]
TYPE_BLACKLIST = ["night_club"]

gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

# Get the logger for this module
logger = logging.getLogger(__name__)


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


def find_restaurants(
    address: str, search_radius: int = 5000
) -> Union[list[dict], None]:
    coordinates = get_coordinates_from_address(address)
    if coordinates:
        latitude, longitude = coordinates
        logger.debug(
            f"Coordinates for {address}: Latitude {latitude}, Longitude {longitude}"
        )
    else:
        logger.error(f"Unable to get coordinates for the address: {address}")
        return None

    restaurants = []

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
                    pub_data = {
                        "gmaps_id": result.get("place_id"),
                        "url": place_details.get("website"),
                        "name": place_details.get("name"),
                        "venue_type": place_details.get("types"),
                        "open_hours": place_details.get("opening_hours", {}).get(
                            "weekday_text"
                        ),
                        "street_address": place_details.get("formatted_address"),
                        "latitude": place_details.get("geometry", {})
                        .get("location", {})
                        .get("lat"),
                        "longitude": place_details.get("geometry", {})
                        .get("location", {})
                        .get("lng"),
                    }
                    restaurants.append(pub_data)
                else:
                    logger.warning(
                        f"Website data not found for {place_details.get('name')}"
                    )

    return restaurants
